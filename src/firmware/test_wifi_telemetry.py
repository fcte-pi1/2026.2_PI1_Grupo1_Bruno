"""FW10: rede simulada e sockets TCP reais locais; sem alegar ensaio físico."""

import errno
import json
import select
import socket
import time
import unittest

from telemetry import TelemetryPublisher
from wifi_telemetry import WifiTelemetry


class FakeWlan:
    def __init__(self, online=True):
        self.online = online
        self.connections = []
        self.disconnects = 0

    def active(self, value):
        self.active_value = value

    def config(self, **values):
        self.configuration = values

    def connect(self, ssid, password):
        self.connections.append((ssid, password))

    def isconnected(self):
        return self.online

    def disconnect(self):
        self.disconnects += 1
        self.online = False


class FakeSocket:
    def __init__(self, connects=None, sends=None):
        self.connects = list(connects or [None])
        self.sends = list(sends or [])
        self.receives = []
        self.flags = 0
        self.output = bytearray()
        self.closed = False
        self.attempts = 0

    def setblocking(self, value):
        self.blocking = value

    def connect(self, address):
        assert self.blocking is False
        self.address = address
        self.attempts += 1
        result = self.connects.pop(0) if self.connects else errno.EISCONN
        if result is not None:
            raise OSError(result)

    def send(self, data):
        assert self.blocking is False
        result = self.sends.pop(0) if self.sends else len(data)
        if isinstance(result, OSError):
            raise result
        count = min(result, len(data)) if result is not None else None
        if count:
            self.output.extend(data[:count])
        return count

    def recv(self, maximum):
        assert self.blocking is False and maximum == 64
        result = self.receives.pop(0)
        if isinstance(result, OSError):
            raise result
        return result

    def close(self):
        self.closed = True


class FakeSockets:
    AF_INET = socket.AF_INET
    SOCK_STREAM = socket.SOCK_STREAM

    def __init__(self, *sockets):
        self.sockets = list(sockets)
        self.calls = 0

    def socket(self, family, kind):
        assert family == self.AF_INET and kind == self.SOCK_STREAM
        self.calls += 1
        return self.sockets.pop(0)


class FakePoll:
    def register(self, sock, mask):
        self.sock = sock
        self.mask = mask

    def modify(self, sock, mask):
        assert sock is self.sock
        self.mask = mask

    def unregister(self, sock):
        assert sock is self.sock

    def poll(self, timeout):
        assert timeout == 0
        if self.sock.flags:
            # MicroPython pode retornar mais de dois itens por evento.
            return [(self.sock, self.sock.flags, "extra")]
        return []


class FakeSelect:
    POLLIN = select.POLLIN
    POLLOUT = select.POLLOUT
    POLLERR = select.POLLERR
    POLLHUP = select.POLLHUP
    POLLNVAL = select.POLLNVAL
    poll = FakePoll


class WifiTests(unittest.TestCase):
    def link(self, *sockets, online=True, **kwargs):
        wlan = FakeWlan(online)
        module = FakeSockets(*sockets)
        link = WifiTelemetry(
            wlan,
            "teste",
            "senha-exemplo",
            "192.168.4.2",
            socket_module=module,
            select_module=FakeSelect,
            **kwargs,
        )
        return link, wlan, module

    def publisher(self, capacity=8):
        return TelemetryPublisher(
            "mouse", "boot", "run-original", "4x4", lambda: self.now, queue_capacity=capacity
        )

    def test_configuration_rejects_dns_and_invalid_addresses_before_network(self):
        for host in (
            "pc.local",
            "example.com",
            "192.168.4.999",
            "192.168.04.2",
            " 192.168.4.2",
            "192.168.4",
            "::1",
            "224.1.2.3",
            "0.0.0.0",
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                WifiTelemetry(None, "test", "", host)
        for port in (0, 65536, True, "8765"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                WifiTelemetry(None, "test", "", "192.168.4.2", port=port)

    def test_absent_wifi_bounded_backoff_and_control_keeps_advancing(self):
        link, wlan, module = self.link(
            online=False, connect_timeout_ms=20, backoff_initial_ms=10, backoff_max_ms=40
        )
        publisher = self.publisher(capacity=3)
        for self.now in range(1000):
            publisher.record_control_cycle()
            publisher.emit("sample", "executando")
            link.service(publisher, self.now)
            self.assertLessEqual(publisher.pending_count, 3)
        self.assertEqual(publisher.stats()["control_cycles"], 1000)
        self.assertGreater(publisher.stats()["samples_dropped"], 0)
        self.assertEqual(module.calls, 0)
        self.assertGreater(wlan.disconnects, 2)
        self.assertLess(len(wlan.connections), 20)
        self.assertEqual(link._backoff, 40)
        self.assertEqual(wlan.configuration, {"reconnects": 0})

    def test_nonblocking_connect_waits_for_completion(self):
        sock = FakeSocket(connects=[errno.EINPROGRESS, errno.EALREADY, errno.EISCONN])
        link, _, _ = self.link(sock)
        self.assertIsNone(link.step(0))
        self.assertFalse(link.connected)
        self.assertIsNone(link.step(1))
        self.assertEqual(sock.attempts, 1)
        sock.flags = select.POLLOUT
        self.assertIsNone(link.step(2))
        self.assertFalse(link.connected)
        self.assertIsNotNone(link.step(3))
        self.assertTrue(link.connected)
        self.assertEqual(sock.attempts, 3)

    def test_connect_error_and_timeout_do_not_send(self):
        for result in (errno.ECONNREFUSED, errno.EINPROGRESS):
            sock = FakeSocket(connects=[result])
            link, _, _ = self.link(sock, connect_timeout_ms=10)
            self.now = 0
            publisher = self.publisher()
            publisher.emit("start", "executando")
            link.service(publisher, 0)
            link.service(publisher, 11)
            self.assertFalse(link.connected)
            self.assertTrue(sock.closed)
            self.assertEqual(sock.output, b"")
            self.assertEqual(publisher.pending_count, 1)

    def test_writable_connect_checks_so_error_before_publishing(self):
        sock = FakeSocket(connects=[errno.EINPROGRESS])
        sock.getsockopt = lambda level, option: errno.ECONNREFUSED
        module = FakeSockets(sock)
        module.SOL_SOCKET = socket.SOL_SOCKET
        module.SO_ERROR = socket.SO_ERROR
        link = WifiTelemetry(
            FakeWlan(), "teste", "", "192.168.4.2", socket_module=module, select_module=FakeSelect
        )
        self.assertIsNone(link.step(0))
        sock.flags = select.POLLOUT
        self.assertIsNone(link.step(1))
        self.assertFalse(link.connected)
        self.assertEqual(link.last_error, errno.ECONNREFUSED)
        self.assertTrue(sock.closed)

    def test_wifi_recovers_without_changing_run(self):
        sock = FakeSocket()
        link, wlan, _ = self.link(sock, online=False)
        self.now = 0
        publisher = self.publisher()
        publisher.emit("start", "executando")
        link.service(publisher, 0)
        self.assertEqual(link.state, "wifi_connecting")
        wlan.online = True
        for self.now in range(1, 100):
            publisher.record_control_cycle()
            link.service(publisher, self.now, 16)
            if not publisher.pending_count:
                break
        self.assertEqual(json.loads(sock.output)["run_id"], "run-original")
        self.assertTrue(link.connected)

    def test_poll_error_disconnects_the_old_stream(self):
        sock = FakeSocket()
        link, _, _ = self.link(sock)
        writer = link.step(0)
        sock.flags = select.POLLHUP | select.POLLERR
        self.assertIsNone(link.step(1))
        self.assertFalse(writer.connected)
        self.assertTrue(sock.closed)

    def test_partial_again_and_wifi_loss_resend_whole_frame(self):
        first = FakeSocket(sends=[7, OSError(errno.EAGAIN), None])
        second = FakeSocket()
        link, wlan, _ = self.link(first, second, backoff_initial_ms=10)
        self.now = 0
        publisher = self.publisher()
        publisher.emit("start", "executando")
        self.assertEqual(link.service(publisher, 0, 16), 7)
        self.assertEqual(link.service(publisher, 1, 16), 0)
        self.assertEqual(link.service(publisher, 2, 16), 0)
        old_writer = link.writer
        wlan.online = False
        link.service(publisher, 3)
        self.assertFalse(old_writer.connected)
        self.assertTrue(first.closed)
        wlan.online = True
        for self.now in range(13, 200):
            publisher.record_control_cycle()
            link.service(publisher, self.now, 16)
            if not publisher.pending_count:
                break
        self.assertIsNot(link.writer, old_writer)
        self.assertTrue(bytes(second.output).startswith(first.output))
        frame = json.loads(second.output.decode().strip())
        self.assertEqual(frame["seq"], 0)
        self.assertEqual(frame["run_id"], "run-original")
        self.assertEqual(frame["event"], "start")
        self.assertEqual(second.output.count(b"\n"), 1)

    def test_write_error_and_app_restart_replace_writer(self):
        first = FakeSocket(sends=[5, OSError(errno.ECONNRESET)])
        second = FakeSocket()
        link, _, _ = self.link(first, second, backoff_initial_ms=10)
        self.now = 0
        publisher = self.publisher()
        publisher.emit("sample", "executando")
        link.service(publisher, 0, 16)
        link.service(publisher, 1, 16)
        self.assertFalse(link.connected)
        self.assertTrue(first.closed)
        for self.now in range(11, 100):
            link.service(publisher, self.now, 32)
            if not publisher.pending_count:
                break
        self.assertEqual(json.loads(second.output)["seq"], 0)

    def test_delayed_peer_stall_timeout_and_control_continue(self):
        sock = FakeSocket(sends=[OSError(errno.EAGAIN)] * 50)
        link, _, _ = self.link(sock, stall_timeout_ms=5)
        self.now = 0
        publisher = self.publisher()
        publisher.emit("sample", "executando")
        for self.now in range(6):
            publisher.record_control_cycle()
            link.service(publisher, self.now)
        self.assertEqual(publisher.stats()["control_cycles"], 6)
        self.assertEqual(link.last_error, "write_timeout")
        self.assertTrue(sock.closed)

    def test_peer_close_and_remote_data_never_change_execution(self):
        sock = FakeSocket()
        link, _, _ = self.link(sock)
        self.now = 0
        publisher = self.publisher()
        link.service(publisher, 0)
        sock.flags = select.POLLIN
        sock.receives = [b'{"command":"start"}\n', b""]
        link.service(publisher, 1)
        self.assertTrue(link.connected)
        self.assertEqual(publisher.run_id, "run-original")
        self.assertEqual(publisher.pending_count, 0)
        link.service(publisher, 2)
        self.assertFalse(link.connected)
        self.assertEqual(link.last_error, "peer_closed")

    def test_backoff_handles_wrapping_ticks_and_close_is_final(self):
        sock = FakeSocket(connects=[errno.ECONNREFUSED])

        def diff(a, b):
            return ((a - b + 128) % 256) - 128

        link, _, module = self.link(sock, ticks_diff=diff, backoff_initial_ms=10, backoff_max_ms=40)
        link.step(250)
        self.assertIsNone(link.step(2))
        self.assertEqual(module.calls, 1)
        link.close()
        self.assertIsNone(link.step(15))
        self.assertEqual(link.state, "closed")


class LocalTcpTests(unittest.TestCase):
    """O caminho SO_ERROR também usa o kernel real, sem ESP32 ou rede externa."""

    def test_localhost_complete_frames_and_reconnect_after_app_restart(self):
        server = socket.socket()
        self.addCleanup(server.close)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        address = server.getsockname()
        server.listen(1)
        server.setblocking(False)
        link = WifiTelemetry(
            FakeWlan(), "teste", "", address[0], address[1], backoff_initial_ms=1, backoff_max_ms=5
        )
        self.addCleanup(link.close)
        start = time.monotonic()

        def now():
            return int((time.monotonic() - start) * 1000)

        publisher = TelemetryPublisher("mouse", "boot", "run-local", "4x4", now)
        publisher.emit("start", "executando")
        accepted = None
        data = bytearray()
        deadline = start + 3
        cycles = 0
        while time.monotonic() < deadline and b"\n" not in data:
            cycles += 1
            publisher.record_control_cycle()
            link.service(publisher, now(), byte_budget=13)
            if accepted is None:
                try:
                    accepted, _ = server.accept()
                    accepted.setblocking(False)
                    self.addCleanup(accepted.close)
                except BlockingIOError:
                    pass
            if accepted is not None:
                try:
                    data.extend(accepted.recv(8192))
                except BlockingIOError:
                    pass
        self.assertGreater(cycles, 1)
        self.assertEqual(json.loads(data)["event"], "start")
        accepted.close()
        server.close()
        # O app fica ausente por um intervalo e depois volta à mesma porta.
        for _ in range(20):
            link.service(publisher, now())
        restarted = socket.socket()
        self.addCleanup(restarted.close)
        restarted.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        restarted.bind(address)
        restarted.listen(1)
        restarted.setblocking(False)
        publisher.emit("sample", "executando")
        data = bytearray()
        accepted = None
        while time.monotonic() < deadline and b"\n" not in data:
            cycles += 1
            publisher.record_control_cycle()
            link.service(publisher, now(), byte_budget=19)
            if accepted is None:
                try:
                    accepted, _ = restarted.accept()
                    accepted.setblocking(False)
                    self.addCleanup(accepted.close)
                except BlockingIOError:
                    pass
            if accepted is not None:
                try:
                    data.extend(accepted.recv(8192))
                except BlockingIOError:
                    pass
        frame = json.loads(data)
        self.assertEqual(frame["event"], "sample")
        self.assertEqual(frame["run_id"], "run-local")
        self.assertEqual(frame["seq"], 1)
        self.assertEqual(publisher.stats()["control_cycles"], cycles)


if __name__ == "__main__":
    unittest.main()
