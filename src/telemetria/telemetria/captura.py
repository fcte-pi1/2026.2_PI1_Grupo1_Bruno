"""Captura de frames JSONL e reprodução pelo mesmo parser do receptor."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO

from telemetria.modelos import Evento, Frame, LinkAberto, LinkFechado
from telemetria.receptor import DecodificadorJSONL, EstatisticasRecepcao, _thread

logger = logging.getLogger(__name__)


async def _abrir_arquivo(caminho: Path, modo: str) -> BinaryIO:
    abertura = asyncio.create_task(asyncio.to_thread(caminho.open, modo))
    try:
        return await asyncio.shield(abertura)
    except asyncio.CancelledError:
        resultado = await asyncio.gather(abertura, return_exceptions=True)
        if not isinstance(resultado[0], BaseException):
            await _thread(resultado[0].close)
        raise


class CapturaJSONL:
    """Salva somente frames validados; erro/limite de disco suspende a captura."""

    def __init__(self, caminho: str | Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes deve ser positivo")
        self.caminho = Path(caminho)
        self.max_bytes = max_bytes
        self.bytes_gravados = 0
        self.saturada = False
        self._arquivo: BinaryIO | None = None

    async def abrir(self) -> None:
        if self._arquivo is None and not self.saturada:
            try:
                self._arquivo = await _abrir_arquivo(self.caminho, "xb")
            except OSError:
                self.saturada = True
                logger.exception("não foi possível abrir captura; gravação suspensa, recepção continua")

    async def gravar(self, frame: Frame) -> None:
        if self.saturada:
            return
        linha = (frame.model_dump_json(exclude_none=True, exclude_defaults=True) + "\n").encode()
        if self.bytes_gravados + len(linha) > self.max_bytes:
            self.saturada = True
            logger.warning("captura atingiu limite de %d bytes; recepção continua", self.max_bytes)
            return
        await self.abrir()
        if self.saturada:
            return
        assert self._arquivo is not None
        try:
            await _thread(self._arquivo.write, linha)
            await _thread(self._arquivo.flush)
        except OSError:
            self.saturada = True
            logger.exception("falha de escrita; captura suspensa, recepção continua")
            with suppress(OSError):
                await self.fechar()
            return
        self.bytes_gravados += len(linha)

    async def fechar(self) -> None:
        if self._arquivo is not None:
            arquivo, self._arquivo = self._arquivo, None
            await _thread(arquivo.close)


class FonteArquivo:
    """Lê JSONL em blocos limitados; não guarda o arquivo todo em memória."""

    simulada = False

    def __init__(self, caminho: str | Path, taxa_hz: float = 10.0, rapido: bool = False) -> None:
        if taxa_hz <= 0:
            raise ValueError("taxa deve ser positiva")
        self.caminho = Path(caminho)
        self.nome = f"arquivo {self.caminho}"
        self.taxa_hz, self.rapido = taxa_hz, rapido
        self.estatisticas = EstatisticasRecepcao()

    async def eventos(self) -> AsyncIterator[Evento]:
        decodificador = DecodificadorJSONL(self.estatisticas)
        arquivo = await _abrir_arquivo(self.caminho, "rb")
        try:
            yield LinkAberto(self.nome)
            while True:
                dados = await _thread(arquivo.read, 1024)
                if not dados:
                    break
                for frame in decodificador.feed(dados):
                    yield frame
                    await asyncio.sleep(0 if self.rapido else 1 / self.taxa_hz)
        finally:
            decodificador.finalizar()
            await _thread(arquivo.close)
        yield LinkFechado("fim do arquivo")
