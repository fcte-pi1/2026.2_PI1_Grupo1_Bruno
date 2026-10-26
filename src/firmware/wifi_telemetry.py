"""Cliente STA/TCP cooperativo para ESP32 MicroPython (FW10).

Execute step() depois do controle local; ele não espera pela rede.
O publisher de telemetry.py mantém a única fila, limitada, de frames.
"""

import errno
import select
import socket
import time

from telemetry import BoundedWriter


def _errno(exc):
    return exc.args[0] if exc.args else None


_PENDING = (errno.EINPROGRESS, errno.EALREADY, errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN))


def _ipv4(host):
    """Aceita apenas IPv4 decimal: connect() não fará consulta DNS/mDNS."""
    if not isinstance(host, str):
        raise ValueError("host deve ser um endereço IPv4 literal")
    parts = host.split(".")
    if len(parts) != 4:
        raise ValueError("host deve ser um endereço IPv4 literal")
    for part in parts:
        if not part or len(part) > 3 or any(c not in "0123456789" for c in part):
            raise ValueError("host deve ser um endereço IPv4 literal")
        if int(part) > 255 or (len(part) > 1 and part[0] == "0"):
            raise ValueError("host deve ser um endereço IPv4 literal")
    if parts[0] == "0" or int(parts[0]) >= 224 or host == "255.255.255.255":
        raise ValueError("host deve identificar um computador IPv4 unicast")
    return host


class WifiTelemetry:
    """Avança uma transição por chamada; não reinicia a execução do robô.

    wlan deve ser network.WLAN(network.WLAN.IF_STA), já criada fora do
    controle. A construção ativa a interface e desliga retries internos.
    socket_module/select_module/ticks_diff permitem testes sem hardware.
    """

    def __init__(
        self,
        wlan,
        ssid,
        password,
        host,
        port=8765,
        connect_timeout_ms=5000,
        stall_timeout_ms=2000,
        backoff_initial_ms=500,
        backoff_max_ms=8000,
        socket_module=socket,
        select_module=select,
        ticks_diff=None,
    ):
        self.address = (_ipv4(host), port)
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("port deve estar entre 1 e 65535")
        if not isinstance(ssid, str) or not ssid or not isinstance(password, str):
            raise ValueError("ssid e password devem ser strings; ssid não pode ser vazio")
        for value in (connect_timeout_ms, stall_timeout_ms, backoff_initial_ms, backoff_max_ms):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError("timeouts e backoff devem ser inteiros positivos")
        if backoff_initial_ms > backoff_max_ms:
            raise ValueError("backoff inicial maior que máximo")
        self.wlan = wlan
        self._ssid = ssid
        self._password = password
        self._socket_module = socket_module
        self._select = select_module
        self._diff = ticks_diff or getattr(time, "ticks_diff", lambda a, b: a - b)
        self._connect_timeout = connect_timeout_ms
        self._stall_timeout = stall_timeout_ms
        self._backoff_initial = backoff_initial_ms
        self._backoff_max = backoff_max_ms
        self._backoff = backoff_initial_ms
        self._wait_ms = 0
        self._since = None
        self._blocked_since = None
        self._now = 0
        self._sock = None
        self._poll = None
        self.writer = None
        self.state = "idle"
        self.last_error = None
        self.reconnects = 0
        # Setup pode levar tempo no driver; faça antes de iniciar os motores.
        wlan.active(True)
        wlan.config(reconnects=0)

    @property
    def connected(self):
        return self.state == "connected" and self.writer is not None and self.writer.connected

    def _dispose_socket(self):
        if self.writer is not None:
            self.writer.disconnect()
        if self._poll is not None and self._sock is not None:
            try:
                self._poll.unregister(self._sock)
            except (OSError, KeyError):
                pass
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._poll = None
        self._blocked_since = None

    def _fail(self, reason, now):
        self._dispose_socket()
        self.last_error = reason
        self.state = "backoff"
        self._since = now
        self._wait_ms = self._backoff
        self._backoff = min(self._backoff * 2, self._backoff_max)
        self.reconnects += 1

    def _established(self):
        self.state = "connected"
        self.last_error = None
        self._poll.modify(self._sock, self._select.POLLIN)
        # Uma nova instância faz o publisher recomeçar um frame parcial do zero.
        self.writer = BoundedWriter(self._write)

    def _start_tcp(self, now):
        self._sock = self._socket_module.socket(self._socket_module.AF_INET, self._socket_module.SOCK_STREAM)
        self._sock.setblocking(False)
        self._poll = self._select.poll()
        self._poll.register(self._sock, self._select.POLLIN | self._select.POLLOUT)
        self.state = "tcp_connecting"
        self._since = now
        try:
            self._sock.connect(self.address)
        except OSError as exc:
            if _errno(exc) == errno.EISCONN:
                self._established()
            elif _errno(exc) not in _PENDING:
                raise
        else:
            self._established()

    def _complete_connect(self):
        # MicroPython ESP32 v1.26 não expõe getsockopt. Lá, uma segunda
        # connect não bloqueante distingue EISCONN de EALREADY/erro do lwIP.
        sm = self._socket_module
        if hasattr(self._sock, "getsockopt") and hasattr(sm, "SO_ERROR"):
            error = self._sock.getsockopt(sm.SOL_SOCKET, sm.SO_ERROR)
            if error:
                raise OSError(error)
            self._established()
            return
        try:
            self._sock.connect(self.address)
        except OSError as exc:
            if _errno(exc) == errno.EISCONN:
                self._established()
            elif _errno(exc) not in _PENDING:
                raise
        else:
            self._established()

    def _write(self, data):
        try:
            sent = self._sock.send(data)
        except OSError as exc:
            if _errno(exc) not in _PENDING:
                raise
            sent = 0
        if sent:
            self._blocked_since = None
            # Só uma transmissão efetiva reinicia o backoff: aceitar TCP e
            # cair imediatamente não cria tempestade de reconexões.
            self._backoff = self._backoff_initial
        elif self._blocked_since is None:
            self._blocked_since = self._now
        return sent or 0

    def step(self, now_ms):
        """Retorna writer conectado ou None; nunca dorme, resolve DNS ou espera I/O."""
        self._now = now_ms
        if self.state == "closed":
            return None
        if self.state == "backoff":
            if self._diff(now_ms, self._since) < self._wait_ms:
                return None
            self.state = "idle"
        try:
            online = self.wlan.isconnected()
            if self.state == "wifi_connecting":
                if online:
                    self._start_tcp(now_ms)
                elif self._diff(now_ms, self._since) >= self._connect_timeout:
                    self.wlan.disconnect()
                    self._fail("wifi_timeout", now_ms)
                return self.writer if self.connected else None
            if self.state == "idle":
                if online:
                    self._start_tcp(now_ms)
                else:
                    self.wlan.connect(self._ssid, self._password)
                    self.state = "wifi_connecting"
                    self._since = now_ms
                return self.writer if self.connected else None
            if not online:
                self._fail("wifi_lost", now_ms)
                return None
            if self.state == "connected" and not self.writer.connected:
                self._fail("write_error", now_ms)
                return None
            if self.state == "tcp_connecting":
                if self._diff(now_ms, self._since) >= self._connect_timeout:
                    self._fail("tcp_timeout", now_ms)
                    return None
            elif (
                self._blocked_since is not None
                and self._diff(now_ms, self._blocked_since) >= self._stall_timeout
            ):
                self._fail("write_timeout", now_ms)
                return None
            # poll(0) e no máximo uma leitura de 64 bytes: dados remotos são
            # descartados, jamais interpretados como comandos de movimento.
            events = self._poll.poll(0)
            if events:
                flags = events[0][1]
                errors = self._select.POLLERR | self._select.POLLHUP | getattr(self._select, "POLLNVAL", 0)
                if flags & errors:
                    self._fail("socket_closed", now_ms)
                    return None
                if self.state == "tcp_connecting" and flags & self._select.POLLOUT:
                    self._complete_connect()
                if self.connected and flags & self._select.POLLIN:
                    try:
                        incoming = self._sock.recv(64)
                    except OSError as exc:
                        if _errno(exc) not in _PENDING:
                            raise
                    else:
                        if not incoming:
                            self._fail("peer_closed", now_ms)
                            return None
        except OSError as exc:
            self._fail(_errno(exc), now_ms)
        return self.writer if self.connected else None

    def service(self, publisher, now_ms, byte_budget=256):
        """Manutenção do link e um envio limitado, após atualizar o controle."""
        writer = self.step(now_ms)
        if writer is None:
            return 0
        sent = publisher.service(writer, byte_budget=byte_budget)
        if not writer.connected:
            self._fail("write_error", now_ms)
        return sent

    def close(self):
        self._dispose_socket()
        self.state = "closed"
