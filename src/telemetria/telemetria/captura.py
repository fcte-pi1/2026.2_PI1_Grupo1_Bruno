"""Captura bruta limitada e playback sem dependência da interface gráfica."""

import asyncio
import base64
import binascii
import json
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO

from telemetria.modelos import Evento, LinkAberto, LinkFechado
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


class CapturaBruta:
    """Envelope JSONL preserva bytes inválidos e fronteiras de reconexão.

    Escrita aguardada aplica backpressure; não mantém fila infinita. Atingido
    max_bytes, suspende a captura e mantém a recepção ativa. Não sobrescreve.
    """

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

    async def _registro(self, registro: dict) -> None:
        if self.saturada:
            return
        linha = (json.dumps({"capture_version": 1, **registro}, separators=(",", ":")) + "\n").encode()
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

    async def gravar(self, dados: bytes) -> None:
        # Limita cada registro mesmo se chamada por outra fonte com blocos enormes.
        for inicio in range(0, len(dados), 1024):
            await self._registro(
                {"type": "data", "data_b64": base64.b64encode(dados[inicio : inicio + 1024]).decode()}
            )

    async def fim_segmento(self) -> None:
        await self._registro({"type": "reset"})

    async def fechar(self) -> None:
        if self._arquivo is not None:
            arquivo, self._arquivo = self._arquivo, None
            await _thread(arquivo.close)


class FonteArquivo:
    """Lê Frames JSONL ou captura envelope, com leitura e memória limitadas."""

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
                linha = await _thread(arquivo.readline, 8193)
                if not linha:
                    break
                if len(linha) > 8192:
                    self.estatisticas.grandes += 1
                    while linha and not linha.endswith(b"\n"):
                        linha = await _thread(arquivo.readline, 8193)
                    continue
                try:
                    registro = json.loads(linha)
                except (ValueError, UnicodeDecodeError, RecursionError):
                    registro = None
                if isinstance(registro, dict) and "capture_version" in registro:
                    try:
                        if registro["capture_version"] != 1:
                            raise ValueError("versão de captura desconhecida")
                        if registro["type"] == "reset":
                            decodificador.finalizar()
                            yield LinkFechado("fim de segmento capturado")
                            yield LinkAberto(self.nome)
                            continue
                        if registro["type"] != "data":
                            raise ValueError("tipo de captura desconhecido")
                        dados = base64.b64decode(registro["data_b64"], validate=True)
                    except (KeyError, ValueError, TypeError, binascii.Error):
                        self.estatisticas.invalidos += 1
                        continue
                else:
                    dados = linha
                for frame in decodificador.feed(dados):
                    yield frame
                    await asyncio.sleep(0 if self.rapido else 1 / self.taxa_hz)
        finally:
            decodificador.finalizar()
            await _thread(arquivo.close)
        yield LinkFechado("fim do arquivo")
