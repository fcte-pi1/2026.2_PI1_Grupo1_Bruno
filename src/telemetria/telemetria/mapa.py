from dataclasses import dataclass

from telemetria.formatacao import ROTULO_ORIGEM
from telemetria.modelos import Frame, Pose

BIT = {"N": 1, "E": 2, "S": 4, "W": 8}
SIMBOLO_POSE = {"N": "triangle-up", "E": "triangle-right", "S": "triangle-down", "W": "triangle-left"}
VIZINHO = {"N": (0, 1, "S"), "S": (0, -1, "N"), "E": (1, 0, "W"), "W": (-1, 0, "E")}

PAREDE = "parede"
LIVRE = "livre"
DESCONHECIDA = "desconhecida"
CONFLITO = "conflito"


@dataclass(frozen=True)
class FalhaMapa:
    t_ms: int
    codigo: str
    mensagem: str
    posicao: tuple[int, int] | None


def _aresta(x: int, y: int, lado: str) -> tuple[str, int, int]:
    return {
        "N": ("h", x, y + 1),
        "S": ("h", x, y),
        "E": ("v", x + 1, y),
        "W": ("v", x, y),
    }[lado]


class EstadoMapa:
    """Mapa, pose, rota e trajeto de uma execução, montados só com o que o robô enviou."""

    def __init__(self) -> None:
        self.versao = 0
        self._limpar(None)

    def _limpar(self, chave: tuple | None) -> None:
        self.chave = chave
        self.largura: int | None = None
        self.altura: int | None = None
        self.celulas: dict[tuple[int, int], tuple[int, int]] = {}
        self.pose: Pose | None = None
        self.rota: list[tuple[int, int]] = []
        self.trajeto: list[tuple[int, int]] = []
        self.falhas: list[FalhaMapa] = []

    def aplicar(self, frame: Frame) -> bool:
        navegacao = getattr(frame, "navigation", None)
        chave = (frame.robot_id, frame.boot_id, frame.run_id, frame.maze_id)
        if frame.event == "start" or (
            chave != self.chave and (frame.map is not None or navegacao is not None)
        ):
            self._limpar(chave)
            self.versao += 1
        if chave != self.chave:
            return False

        mudou = False
        dimensoes = (
            (frame.map.width, frame.map.height)
            if frame.map is not None
            else (navegacao.width, navegacao.height)
            if navegacao is not None
            else None
        )
        if dimensoes is not None and dimensoes != (self.largura, self.altura):
            if self.largura is not None:
                self._limpar(chave)
            self.largura, self.altura = dimensoes
            mudou = True

        if frame.map is not None:
            for celula in frame.map.cells:
                self.celulas[(celula.x, celula.y)] = (celula.walls, celula.known)
            mudou = True

        if navegacao is not None:
            if navegacao.pose is not None:
                self.pose = navegacao.pose
                posicao = (navegacao.pose.x, navegacao.pose.y)
                if not self.trajeto or self.trajeto[-1] != posicao:
                    self.trajeto.append(posicao)
            if navegacao.route is not None:
                self.rota = [(c.x, c.y) for c in navegacao.route.cells]
            mudou = True

        if frame.fault is not None:
            posicao = (self.pose.x, self.pose.y) if self.pose is not None else None
            self.falhas.append(FalhaMapa(frame.t_ms, frame.fault.code, frame.fault.message, posicao))
            mudou = True

        if mudou:
            self.versao += 1
        return mudou

    def estado_aresta(self, x: int, y: int, lado: str) -> str:
        dx, dy, oposto = VIZINHO[lado]
        leituras = []
        for cx, cy, cl in ((x, y, lado), (x + dx, y + dy, oposto)):
            if (cx, cy) in self.celulas:
                paredes, conhecidas = self.celulas[(cx, cy)]
                if conhecidas & BIT[cl]:
                    leituras.append(PAREDE if paredes & BIT[cl] else LIVRE)
        if not leituras:
            return DESCONHECIDA
        if len(set(leituras)) > 1:
            return CONFLITO
        return leituras[0]

    def arestas(self) -> dict[tuple[str, int, int], str]:
        if self.largura is None:
            return {}
        estados = {}
        for x in range(self.largura):
            for y in range(self.altura):
                for lado in "NESW":
                    estados.setdefault(_aresta(x, y, lado), self.estado_aresta(x, y, lado))
        return estados

    def resumo(self) -> dict:
        return {
            "chave": self.chave,
            "dimensoes": (self.largura, self.altura),
            "celulas": sorted(self.celulas.items()),
            "pose": self.pose,
            "rota": list(self.rota),
            "trajeto": list(self.trajeto),
            "falhas": list(self.falhas),
        }


def _segmentos(arestas: list[tuple[str, int, int]]) -> tuple[list, list]:
    xs, ys = [], []
    for tipo, a, b in arestas:
        if tipo == "h":
            xs += [a, a + 1, None]
            ys += [b, b, None]
        else:
            xs += [a, a, None]
            ys += [b, b + 1, None]
    return xs, ys


def _centros(posicoes: list[tuple[int, int]]) -> tuple[list[float], list[float]]:
    return [x + 0.5 for x, _ in posicoes], [y + 0.5 for _, y in posicoes]


def figura_mapa(estado: EstadoMapa) -> dict:
    if estado.largura is None:
        return {
            "data": [],
            "layout": {
                "xaxis": {"visible": False},
                "yaxis": {"visible": False},
                "annotations": [{"text": "Sem dados de mapa", "showarrow": False, "font": {"size": 16}}],
                "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
            },
        }

    por_estado: dict[str, list] = {PAREDE: [], DESCONHECIDA: [], CONFLITO: []}
    for aresta, situacao in estado.arestas().items():
        if situacao in por_estado:
            por_estado[situacao].append(aresta)

    dados = []
    for situacao, nome, linha in (
        (DESCONHECIDA, "Parede desconhecida", {"color": "#c0c0c0", "width": 1, "dash": "dot"}),
        (PAREDE, "Parede", {"color": "#222222", "width": 4}),
        (CONFLITO, "Leituras conflitantes", {"color": "#d62728", "width": 4}),
    ):
        xs, ys = _segmentos(por_estado[situacao])
        if xs:
            dados.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": nome,
                    "x": xs,
                    "y": ys,
                    "line": linha,
                    "hoverinfo": "skip",
                }
            )

    if len(estado.trajeto) > 1:
        xs, ys = _centros(estado.trajeto)
        dados.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Trajeto executado",
                "x": xs,
                "y": ys,
                "line": {"color": "#1f77b4", "width": 3},
            }
        )
    if len(estado.rota) > 1:
        xs, ys = _centros(estado.rota)
        dados.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Rota planejada",
                "x": xs,
                "y": ys,
                "line": {"color": "#ff7f0e", "width": 2, "dash": "dash"},
            }
        )
    falhas = [f for f in estado.falhas if f.posicao is not None]
    if falhas:
        xs, ys = _centros([f.posicao for f in falhas])
        dados.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Falha",
                "x": xs,
                "y": ys,
                "text": [f"{f.codigo}: {f.mensagem}" for f in falhas],
                "marker": {"symbol": "x", "size": 12, "color": "#d62728"},
            }
        )
    if estado.pose is not None:
        xs, ys = _centros([(estado.pose.x, estado.pose.y)])
        dados.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": f"Robô ({estado.pose.heading}, {ROTULO_ORIGEM[estado.pose.source]})",
                "x": xs,
                "y": ys,
                "marker": {"symbol": SIMBOLO_POSE[estado.pose.heading], "size": 18, "color": "#2ca02c"},
            }
        )

    celulas = [
        {
            "type": "rect",
            "x0": x,
            "y0": y,
            "x1": x + 1,
            "y1": y + 1,
            "line": {"width": 0},
            "fillcolor": "rgba(31, 119, 180, 0.08)",
            "layer": "below",
        }
        for (x, y), (_, conhecidas) in estado.celulas.items()
        if conhecidas
    ]
    return {
        "data": dados,
        "layout": {
            "shapes": celulas,
            "margin": {"l": 30, "r": 10, "t": 10, "b": 30},
            "xaxis": {
                "range": [-0.2, estado.largura + 0.2],
                "showgrid": False,
                "zeroline": False,
                "tickvals": [x + 0.5 for x in range(estado.largura)],
                "ticktext": [str(x) for x in range(estado.largura)],
            },
            "yaxis": {
                "range": [-0.2, estado.altura + 0.2],
                "showgrid": False,
                "zeroline": False,
                "scaleanchor": "x",
                "tickvals": [y + 0.5 for y in range(estado.altura)],
                "ticktext": [str(y) for y in range(estado.altura)],
            },
            "legend": {"orientation": "h", "y": -0.12},
            "uirevision": "mapa",
        },
    }
