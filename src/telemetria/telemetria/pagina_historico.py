from pathlib import Path

from nicegui import run, ui

from telemetria.armazenamento import Armazenamento, ResumoExecucao
from telemetria.formatacao import texto_tempo
from telemetria.historico import CABECALHO, ROTULO_STATUS, linhas_tabela, texto_origens, texto_status
from telemetria.mapa import figura_mapa
from telemetria.modelos import Frame
from telemetria.replay import VELOCIDADES, Replay

TODOS = "todos"
PASSO_S = 0.1


def _consultar(
    caminho: Path, maze_id: str | None, status: str | None
) -> tuple[list[str], list[ResumoExecucao]]:
    # Conexão própria só de leitura: a consulta não disputa a thread que grava a coleta.
    if not caminho.is_file():
        return [], []
    with Armazenamento(caminho, somente_leitura=True) as banco:
        return banco.labirintos(), banco.execucoes(maze_id=maze_id, status=status)


def _carregar_execucao(caminho: Path, execucao_id: int) -> tuple[ResumoExecucao | None, list[Frame]]:
    if not caminho.is_file():
        return None, []
    with Armazenamento(caminho, somente_leitura=True) as banco:
        return banco.execucao(execucao_id), banco.frames(execucao_id)


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
        tabela = ui.table(columns=colunas, rows=[], row_key="id").classes("w-full cursor-pointer")
        tabela.on("rowClick", lambda e: ui.navigate.to(f"/replay/{e.args[1]['id']}"))
        ui.label("Clique numa execução para abrir o replay.").classes("text-xs text-gray-500")
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

    @ui.page("/replay/{execucao_id}")
    async def pagina_replay(execucao_id: int) -> None:
        ui.page_title("Replay - Telemetria Micromouse")
        with ui.header().classes("items-center justify-between bg-slate-800"):
            ui.label("Replay da execução").classes("text-xl font-bold")
            ui.link("Histórico", "/historico").classes("text-white")

        resumo, frames = await run.io_bound(_carregar_execucao, caminho, execucao_id)
        if resumo is None:
            ui.label("Execução não encontrada.").classes("text-gray-500")
            return
        ui.label(
            f"{resumo.run_id} | labirinto {resumo.maze_id or '—'} | {texto_status(resumo)} | "
            f"origem: {texto_origens(resumo)}"
        ).classes("text-gray-700")
        if not frames:
            ui.label("Esta execução não tem dados salvos para reproduzir.").classes("text-gray-500")
            return

        replay = Replay(frames)
        grafico = ui.plotly(figura_mapa(replay.estado(0))).classes("w-full h-[28rem]")

        with ui.row().classes("items-center gap-4 w-full"):
            tocar = ui.button(icon="play_arrow")
            velocidade = ui.select(
                {v: f"{v:g}x" for v in VELOCIDADES}, value=1.0, label="Velocidade"
            ).classes("w-28")
            tempo = ui.label().classes("font-mono")
        fim_slider = max(replay.fim_ms, replay.inicio_ms + 1)
        linha_tempo = ui.slider(min=replay.inicio_ms, max=fim_slider, value=replay.inicio_ms, step=1).classes(
            "w-full"
        )

        with ui.card().classes("w-full"):
            ui.label("Falhas registradas").classes("text-lg font-bold")
            if not replay.final.falhas:
                ui.label("Nenhuma falha nesta execução.").classes("text-gray-500")
            for falha in replay.final.falhas:
                onde = "posição desconhecida" if falha.posicao is None else f"célula {falha.posicao}"
                quando = texto_tempo(falha.t_ms - replay.inicio_ms)
                ui.label(f"{quando} | {falha.codigo}: {falha.mensagem} ({onde})").classes("font-mono text-sm")

        visto = {"aplicados": -1, "tocando": False}

        def mostrar() -> None:
            t_ms = int(linha_tempo.value)
            aplicados = replay.aplicados_ate(t_ms)
            tempo.set_text(
                f"{texto_tempo(t_ms - replay.inicio_ms)} / {texto_tempo(replay.fim_ms - replay.inicio_ms)}"
                f" | mensagem {aplicados} de {replay.total}"
            )
            if aplicados != visto["aplicados"]:
                visto["aplicados"] = aplicados
                grafico.update_figure(figura_mapa(replay.estado(aplicados)))

        def alternar() -> None:
            if not visto["tocando"] and linha_tempo.value >= replay.fim_ms:
                linha_tempo.set_value(replay.inicio_ms)
            visto["tocando"] = not visto["tocando"]
            tocar.props(f"icon={'pause' if visto['tocando'] else 'play_arrow'}")

        def avancar() -> None:
            if not visto["tocando"]:
                return
            proximo = linha_tempo.value + PASSO_S * 1000 * velocidade.value
            if proximo >= replay.fim_ms:
                proximo = replay.fim_ms
                alternar()
            linha_tempo.set_value(proximo)

        tocar.on_click(alternar)
        linha_tempo.on_value_change(mostrar)
        ui.timer(PASSO_S, avancar)
        mostrar()
