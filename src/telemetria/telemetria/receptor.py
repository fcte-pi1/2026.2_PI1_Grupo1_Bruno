"""Fontes JSONL passivas. Nunca transmitem comandos ao robô."""

import asyncio
import json
import logging
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from telemetria.modelos import MAX_FRAME_BYTES, Evento, Frame, LinkAberto, LinkFechado

logger = logging.getLogger(__name__)
MAX_PAYLOAD = MAX_FRAME_BYTES


@dataclass
class EstatisticasRecepcao:
    frames: int = 0
    invalidos: int = 0
    grandes: int = 0
    incompletos: int = 0
    amostras_descartadas: int = 0
    conexoes: int = 0


def _objeto_sem_duplicadas(pares: list[tuple[str, Any]]) -> dict[str, Any]:
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError("chave JSON duplicada")
        objeto[chave] = valor
    return objeto


def _constante_invalida(valor: str) -> Any:
    raise ValueError(f"constante JSON não finita: {valor}")


class DecodificadorJSONL:
    """LF termina payload de até 4096 bytes; overflow descarta até o próximo LF."""

    def __init__(self, estatisticas: EstatisticasRecepcao | None = None) -> None:
        self.estatisticas = estatisticas or EstatisticasRecepcao()
        self._buffer = bytearray()
        self._descartando = False

    def feed(self, dados: bytes) -> list[Frame]:
        frames = []
        partes = dados.split(b"\n")
        for indice, parte in enumerate(partes):
            if not self._descartando:
                if len(self._buffer) + len(parte) > MAX_PAYLOAD:
                    self.estatisticas.grandes += 1
                    self._buffer.clear()
                    self._descartando = True
                    logger.warning("payload maior que %d bytes; aguardando LF", MAX_PAYLOAD)
                else:
                    self._buffer.extend(parte)
            if indice == len(partes) - 1:
                continue
            if not self._descartando:
                try:
                    # Decodificar explicitamente impede aceitação de UTF-8 substituído.
                    texto = self._buffer.decode("utf-8", errors="strict")
                    json.loads(
                        texto, object_pairs_hook=_objeto_sem_duplicadas, parse_constant=_constante_invalida
                    )
                    frame = Frame.model_validate_json(texto)
                except (UnicodeDecodeError, ValidationError, ValueError, RecursionError):
                    self.estatisticas.invalidos += 1
                    logger.debug("linha rejeitada: UTF-8, JSON ou contrato inválido")
                else:
                    self.estatisticas.frames += 1
                    frames.append(frame)
            self._buffer.clear()
            self._descartando = False
        return frames

    def finalizar(self) -> None:
        if self._buffer or self._descartando:
            self.estatisticas.incompletos += 1
        self._buffer.clear()
        self._descartando = False


class _FilaEventos:
    """Preserva ordem. Cheia: remove sample antigo; só críticos: backpressure."""

    def __init__(self, capacidade: int, estatisticas: EstatisticasRecepcao) -> None:
        if capacidade < 1:
            raise ValueError("fila_max deve ser positiva")
        self.capacidade = capacidade
        self.estatisticas = estatisticas
        self._itens: deque[Evento] = deque()
        self._condicao = asyncio.Condition()

    async def colocar(self, evento: Evento) -> None:
        async with self._condicao:
            while len(self._itens) >= self.capacidade:
                indice = next(
                    (
                        i
                        for i, item in enumerate(self._itens)
                        if isinstance(item, Frame) and item.event == "sample"
                    ),
                    None,
                )
                if indice is not None:
                    del self._itens[indice]
                    self.estatisticas.amostras_descartadas += 1
                    break
                if isinstance(evento, Frame) and evento.event == "sample":
                    self.estatisticas.amostras_descartadas += 1
                    return
                await self._condicao.wait()
            self._itens.append(evento)
            self._condicao.notify_all()

    async def retirar(self) -> Evento:
        async with self._condicao:
            await self._condicao.wait_for(lambda: bool(self._itens))
            evento = self._itens.popleft()
            self._condicao.notify_all()
            return evento


async def _thread(funcao: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Espera a operação finita encerrar antes de fechar o recurso na thread."""
    tarefa = asyncio.create_task(asyncio.to_thread(funcao, *args, **kwargs))
    try:
        return await asyncio.shield(tarefa)
    except asyncio.CancelledError:
        await asyncio.gather(tarefa, return_exceptions=True)
        raise


class _FonteReceptora:
    simulada = False

    def __init__(self, fila_max: int = 256, captura: Any = None) -> None:
        self.estatisticas = EstatisticasRecepcao()
        self._fila = _FilaEventos(fila_max, self.estatisticas)
        self._captura = captura
        self._rodando = False

    async def _receber(self, dados: bytes, decodificador: DecodificadorJSONL) -> None:
        if self._captura is not None:
            await self._captura.gravar(dados)
        for frame in decodificador.feed(dados):
            await self._fila.colocar(frame)

    async def _produzir(self) -> None:
        raise NotImplementedError

    async def eventos(self) -> AsyncIterator[Evento]:
        if self._rodando:
            raise RuntimeError("fonte já possui consumidor")
        self._rodando = True
        produtor = asyncio.create_task(self._produzir())
        try:
            while True:
                retirada = asyncio.create_task(self._fila.retirar())
                try:
                    prontos, _ = await asyncio.wait({retirada, produtor}, return_when=asyncio.FIRST_COMPLETED)
                    if retirada in prontos:
                        yield retirada.result()
                    else:
                        produtor.result()
                        return
                finally:
                    retirada.cancel()
                    await asyncio.gather(retirada, return_exceptions=True)
        finally:
            produtor.cancel()
            await asyncio.gather(produtor, return_exceptions=True)
            self._rodando = False


class FonteSerial(_FonteReceptora):
    def __init__(
        self,
        porta: str,
        baud: int = 115200,
        timeout_s: float = 0.1,
        reconexao_s: float = 1.0,
        fila_max: int = 256,
        captura: Any = None,
    ) -> None:
        super().__init__(fila_max, captura)
        if baud <= 0 or timeout_s <= 0 or reconexao_s < 0:
            raise ValueError("baud/timeout devem ser positivos; reconexão não negativa")
        self.porta, self.baud = porta, baud
        self.timeout_s, self.reconexao_s = timeout_s, reconexao_s
        self.nome = f"serial {porta} ({baud} baud)"

    async def _produzir(self) -> None:
        import serial

        espera = self.reconexao_s
        while True:
            porta = None
            decodificador = DecodificadorJSONL(self.estatisticas)
            try:
                # Abrir é curto; cancelamento sempre recolhe/fecha uma porta recém-aberta.
                abertura = asyncio.create_task(
                    asyncio.to_thread(
                        serial.serial_for_url,
                        self.porta,
                        baudrate=self.baud,
                        timeout=self.timeout_s,
                        write_timeout=self.timeout_s,
                    )
                )
                try:
                    porta = await asyncio.shield(abertura)
                except asyncio.CancelledError:
                    resultado = await asyncio.gather(abertura, return_exceptions=True)
                    if not isinstance(resultado[0], BaseException):
                        porta = resultado[0]
                    raise
                self.estatisticas.conexoes += 1
                espera = self.reconexao_s
                await self._fila.colocar(LinkAberto(self.nome))
                while True:
                    dados = await _thread(porta.read, 1024)
                    if dados:
                        await self._receber(dados, decodificador)
            except serial.SerialException as erro:
                logger.warning("serial indisponível: %s", erro)
                await self._fila.colocar(LinkFechado(str(erro)))
            finally:
                decodificador.finalizar()
                try:
                    if porta is not None:
                        await _thread(porta.close)
                finally:
                    if self._captura is not None:
                        await self._captura.fim_segmento()
            await asyncio.sleep(espera)
            espera = min(10.0, espera * 2)


class FonteTCPListen(_FonteReceptora):
    """O PC escuta; o ESP32 em STA conecta como cliente. Um cliente por vez."""

    def __init__(
        self, host: str, porta: int, fila_max: int = 256, captura: Any = None, timeout_s: float = 0.5
    ) -> None:
        super().__init__(fila_max, captura)
        if not 0 <= porta <= 65535 or timeout_s <= 0:
            raise ValueError("porta/timeout inválido")
        self.host, self.porta, self.timeout_s = host, porta, timeout_s
        self.nome = f"TCP {host}:{porta}"
        self.porta_efetiva: int | None = None
        self._cliente_ativo = False
        self._clientes: set[asyncio.Task[Any]] = set()

    async def _cliente(self, leitor: asyncio.StreamReader, escritor: asyncio.StreamWriter) -> None:
        tarefa = asyncio.current_task()
        assert tarefa is not None
        self._clientes.add(tarefa)
        decodificador = DecodificadorJSONL(self.estatisticas)
        aceito = not self._cliente_ativo
        if aceito:
            self._cliente_ativo = True
        try:
            if not aceito:
                return
            self.estatisticas.conexoes += 1
            await self._fila.colocar(LinkAberto(f"{self.nome}: {escritor.get_extra_info('peername')}"))
            while True:
                try:
                    dados = await asyncio.wait_for(leitor.read(1024), timeout=self.timeout_s)
                except TimeoutError:
                    # Silêncio não encerra run nem reconecta: EstadoPainel indica stale.
                    continue
                if not dados:
                    break
                await self._receber(dados, decodificador)
        except (ConnectionError, OSError) as erro:
            logger.warning("TCP desconectado: %s", erro)
        finally:
            decodificador.finalizar()
            escritor.close()
            with suppress(ConnectionError, OSError, TimeoutError):
                await asyncio.wait_for(escritor.wait_closed(), timeout=1.0)
            try:
                if aceito:
                    if self._captura is not None:
                        await self._captura.fim_segmento()
                    if not tarefa.cancelling():
                        await self._fila.colocar(LinkFechado("cliente TCP desconectado"))
            finally:
                if aceito:
                    self._cliente_ativo = False
                self._clientes.discard(tarefa)

    async def _produzir(self) -> None:
        servidor = await asyncio.start_server(self._cliente, self.host, self.porta, limit=8192)
        self.porta_efetiva = servidor.sockets[0].getsockname()[1]
        logger.info("aguardando ESP32 em %s:%s", self.host, self.porta_efetiva)
        try:
            async with servidor:
                await servidor.serve_forever()
        finally:
            clientes = list(self._clientes)
            for cliente in clientes:
                cliente.cancel()
            await asyncio.gather(*clientes, return_exceptions=True)
            self.porta_efetiva = None
