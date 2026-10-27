from nicegui import ui

from telemetria.estado import Amostra, Conexao, EstadoPainel
from telemetria.formatacao import cor_origem, texto_leitura, texto_origem, texto_tempo
from telemetria.mapa import figura_mapa
from telemetria.modelos import Leitura

COR_CONEXAO = {
    Conexao.AGUARDANDO: "grey",
    Conexao.CONECTADO: "positive",
    Conexao.DESATUALIZADO: "warning",
    Conexao.DESCONECTADO: "negative",
}

NIVEL_LOG = {"info": "INFO", "aviso": "AVISO", "erro": "ERRO"}


def figura(amostras: list[Amostra]) -> dict:
    t = [a.t_s for a in amostras]
    series = [
        ("Roda esquerda", [a.esquerda for a in amostras], "#1f77b4", "solid"),
        ("Alvo esquerda", [a.alvo_esquerda for a in amostras], "#1f77b4", "dot"),
        ("Roda direita", [a.direita for a in amostras], "#d62728", "solid"),
        ("Alvo direita", [a.alvo_direita for a in amostras], "#d62728", "dot"),
    ]
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines",
                "name": nome,
                "x": t,
                "y": y,
                "line": {"color": cor, "dash": traco},
                "connectgaps": False,
            }
            for nome, y, cor, traco in series
        ],
        "layout": {
            "margin": {"l": 50, "r": 20, "t": 30, "b": 40},
            "xaxis": {"title": {"text": "tempo do robô (s)"}},
            "yaxis": {"title": {"text": "velocidade (mm/s)"}},
            "legend": {"orientation": "h", "y": 1.15},
            "uirevision": "fixo",
        },
    }


class CampoLeitura:
    def __init__(self, rotulo: str) -> None:
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            ui.label(rotulo).classes("text-gray-600")
            with ui.row().classes("items-center gap-2 no-wrap"):
                self._valor = ui.label("indisponível").classes("font-mono text-lg")
                self._origem = ui.badge("").props("outline")

    def mostrar(self, leitura: Leitura | None, casas: int = 1) -> None:
        self._valor.set_text(texto_leitura(leitura, casas))
        self._origem.set_text(texto_origem(leitura))
        self._origem.props(f"color={cor_origem(leitura)}")
        self._origem.set_visibility(leitura is not None)


def criar_pagina(
    estado: EstadoPainel, fonte_simulada: bool, intervalo_s: float = 0.25, historico: bool = False
) -> None:
    @ui.page("/")
    def pagina() -> None:
        ui.page_title("Telemetria Micromouse")

        with ui.header().classes("items-center justify-between bg-slate-800"):
            ui.label("Telemetria Micromouse").classes("text-xl font-bold")
            with ui.row().classes("items-center gap-3"):
                if historico:
                    ui.link("Histórico", "/historico").classes("text-white")
                if fonte_simulada:
                    ui.badge("FONTE SIMULADA", color="orange").classes("text-sm")
                selo = ui.badge("aguardando", color="grey").classes("text-sm")
                idade = ui.label("").classes("text-sm text-gray-300")

        aviso = ui.label("").classes("w-full text-center bg-amber-100 text-amber-900 p-2 rounded")
        aviso.set_visibility(False)

        with ui.row().classes("w-full gap-4 items-stretch") as cartoes:
            with ui.card().classes("min-w-64 flex-1"):
                ui.label("Execução").classes("text-lg font-bold")
                campos_execucao = {}
                for chave, rotulo in (
                    ("state", "Estado"),
                    ("run_id", "Execução"),
                    ("maze_id", "Labirinto"),
                    ("tempo", "Tempo do robô"),
                    ("seq", "Sequência"),
                    ("descartados", "Descartadas"),
                ):
                    with ui.row().classes("justify-between w-full"):
                        ui.label(rotulo).classes("text-gray-600")
                        campos_execucao[chave] = ui.label("—").classes("font-mono")

            with ui.card().classes("min-w-72 flex-1"):
                ui.label("Rodas e controle").classes("text-lg font-bold")
                vel_esq = CampoLeitura("Velocidade esquerda")
                alvo_esq = CampoLeitura("Alvo esquerda")
                vel_dir = CampoLeitura("Velocidade direita")
                alvo_dir = CampoLeitura("Alvo direita")
                erro = CampoLeitura("Erro do controle")

            with ui.card().classes("min-w-64 flex-1"):
                ui.label("Sensores").classes("text-lg font-bold")
                area_sensores = ui.column().classes("w-full gap-1")
                campos_sensores: dict[str, CampoLeitura] = {}

            with ui.card().classes("min-w-56 flex-1"):
                ui.label("Bateria").classes("text-lg font-bold")
                tensao = CampoLeitura("Tensão")
                ui.label("Percentual de carga não estimado").classes("text-xs text-gray-500")

        with ui.card().classes("w-full"):
            ui.label("Velocidade das rodas (últimos 30 s)").classes("text-lg font-bold")
            grafico = ui.plotly(figura([])).classes("w-full h-80")

        with ui.card().classes("w-full"):
            ui.label("Mapa descoberto").classes("text-lg font-bold")
            ui.label("Só aparece o que o robô enviou: parede pontilhada ainda não foi observada.").classes(
                "text-xs text-gray-500"
            )
            grafico_mapa = ui.plotly(figura_mapa(estado.mapa)).classes("w-full h-96")

        with ui.card().classes("w-full"):
            ui.label("Eventos e falhas").classes("text-lg font-bold")
            log = ui.log(max_lines=200).classes("w-full h-48")

        visto = {"versao": -1, "log": 0, "mapa": -1}

        def atualizar() -> None:
            conexao = estado.conexao()
            selo.set_text(conexao.value)
            selo.props(f"color={COR_CONEXAO[conexao]}")
            segundos = estado.segundos_desde_ultima_mensagem()
            idade.set_text("" if segundos is None else f"última mensagem há {segundos:.1f} s")

            desatualizado = conexao in (Conexao.DESATUALIZADO, Conexao.DESCONECTADO)
            aviso.set_visibility(desatualizado and estado.ultimo_frame is not None)
            aviso.set_text(f"Valores congelados: sem mensagens novas ({conexao.value})")
            if desatualizado:
                cartoes.classes(add="opacity-50")
            else:
                cartoes.classes(remove="opacity-50")

            for registro in estado.log:
                if registro.numero > visto["log"]:
                    hora = registro.instante.strftime("%H:%M:%S")
                    log.push(f"{hora} [{NIVEL_LOG[registro.nivel]}] {registro.texto}")
                    visto["log"] = registro.numero

            if estado.versao == visto["versao"]:
                return
            visto["versao"] = estado.versao

            frame = estado.ultimo_frame
            if frame is None:
                return
            campos_execucao["state"].set_text(frame.state)
            campos_execucao["run_id"].set_text(frame.run_id or "—")
            campos_execucao["maze_id"].set_text(frame.maze_id or "—")
            campos_execucao["tempo"].set_text(texto_tempo(frame.t_ms))
            campos_execucao["seq"].set_text(str(frame.seq))
            campos_execucao["descartados"].set_text(str(estado.descartados))

            vel_esq.mostrar(frame.wheel_left.speed if frame.wheel_left else None)
            alvo_esq.mostrar(frame.wheel_left.target if frame.wheel_left else None)
            vel_dir.mostrar(frame.wheel_right.speed if frame.wheel_right else None)
            alvo_dir.mostrar(frame.wheel_right.target if frame.wheel_right else None)
            erro.mostrar(frame.control_error)
            tensao.mostrar(frame.battery_voltage, casas=2)

            for nome in sorted(set(campos_sensores) | set(frame.sensors)):
                if nome not in campos_sensores:
                    with area_sensores:
                        campos_sensores[nome] = CampoLeitura(nome.capitalize())
                campos_sensores[nome].mostrar(frame.sensors.get(nome))

            grafico.update_figure(figura(estado.amostras_na_janela()))
            if estado.mapa.versao != visto["mapa"]:
                visto["mapa"] = estado.mapa.versao
                grafico_mapa.update_figure(figura_mapa(estado.mapa))

        ui.timer(intervalo_s, atualizar)
