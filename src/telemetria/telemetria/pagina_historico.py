from pathlib import Path

from nicegui import run, ui

from telemetria.armazenamento import Armazenamento, ResumoExecucao
from telemetria.historico import CABECALHO, ROTULO_STATUS, linhas_tabela

TODOS = "todos"


def _consultar(
    caminho: Path, maze_id: str | None, status: str | None
) -> tuple[list[str], list[ResumoExecucao]]:
    # Conexão própria só de leitura: a consulta não disputa a thread que grava a coleta.
    if not caminho.is_file():
        return [], []
    with Armazenamento(caminho, somente_leitura=True) as banco:
        return banco.labirintos(), banco.execucoes(maze_id=maze_id, status=status)


def criar_pagina_historico(caminho_banco: str | Path) -> None:
    caminho = Path(caminho_banco)

    @ui.page("/historico")
    async def pagina() -> None:
        ui.page_title("Histórico - Telemetria Micromouse")
        with ui.header().classes("items-center justify-between bg-slate-800"):
            ui.label("Histórico de execuções").classes("text-xl font-bold")
            ui.link("Painel ao vivo", "/").classes("text-white")

        with ui.row().classes("items-end gap-4"):
            labirinto = ui.select({TODOS: "Todos os labirintos"}, value=TODOS, label="Labirinto").classes(
                "w-56"
            )
            estado = ui.select(
                {TODOS: "Todos", **ROTULO_STATUS}, value=TODOS, label="Estado da execução"
            ).classes("w-56")
            atualizar = ui.button("Atualizar", icon="refresh")

        colunas = [
            {"name": str(i), "label": nome, "field": str(i), "align": "left"}
            for i, nome in enumerate(CABECALHO)
        ]
        tabela = ui.table(columns=colunas, rows=[], row_key="id").classes("w-full")
        vazio = ui.label("Nenhuma execução encontrada.").classes("text-gray-500")

        async def carregar() -> None:
            maze_id = None if labirinto.value == TODOS else labirinto.value
            status = None if estado.value == TODOS else estado.value
            labirintos, resumos = await run.io_bound(_consultar, caminho, maze_id, status)
            labirinto.set_options(
                {TODOS: "Todos os labirintos", **{m: m for m in labirintos}}, value=labirinto.value
            )
            tabela.rows = [
                {"id": resumo.id, **{str(i): valor for i, valor in enumerate(linha)}}
                for resumo, linha in zip(resumos, linhas_tabela(resumos), strict=True)
            ]
            tabela.update()
            vazio.set_visibility(not resumos)

        labirinto.on_value_change(carregar)
        estado.on_value_change(carregar)
        atualizar.on_click(carregar)
        await carregar()
