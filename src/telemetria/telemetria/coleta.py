from collections.abc import AsyncIterator
from typing import Protocol

from telemetria.estado import EstadoPainel
from telemetria.modelos import Evento, Frame, LinkAberto, LinkFechado


class Fonte(Protocol):
    simulada: bool
    nome: str

    def eventos(self) -> AsyncIterator[Evento]: ...


def aplicar(evento: Evento, estado: EstadoPainel) -> None:
    if isinstance(evento, Frame):
        estado.registrar(evento)
    elif isinstance(evento, LinkAberto):
        estado.link_aberto(evento.descricao)
    elif isinstance(evento, LinkFechado):
        estado.link_fechado(evento.motivo)


async def coletar(fonte: Fonte, estado: EstadoPainel) -> None:
    async for evento in fonte.eventos():
        aplicar(evento, estado)
