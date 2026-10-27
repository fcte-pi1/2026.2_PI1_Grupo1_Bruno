import asyncio
import random
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable

from telemetria.modelos import (
    VERSAO_CONTRATO,
    AtualizacaoMapa,
    Celula,
    Evento,
    Falha,
    Frame,
    FrameV2,
    Leitura,
    LinkAberto,
    LinkFechado,
    Navegacao,
    Pose,
    Posicao,
    Roda,
    RotaPlanejada,
)

SENSORES = ("frontal", "esquerda", "direita")
DELTA = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
OPOSTO = {"N": "S", "E": "W", "S": "N", "W": "E"}
BIT_LADO = {"N": 1, "E": 2, "S": 4, "W": 8}
REPUBLICAR_ROTA = 10


def dimensoes_labirinto(maze_id: str) -> tuple[int, int]:
    largura, separador, altura = maze_id.partition("x")
    if not separador or not largura.isdigit() or not altura.isdigit():
        raise ValueError(f"labirinto deve ser LARGURAxALTURA, recebido {maze_id!r}")
    dimensoes = int(largura), int(altura)
    if not all(1 <= d <= 32 for d in dimensoes):
        raise ValueError("dimensões do labirinto devem estar entre 1 e 32")
    return dimensoes


def gerar_labirinto(largura: int, altura: int, rng: random.Random) -> dict[tuple[int, int], int]:
    paredes = {(x, y): 15 for x in range(largura) for y in range(altura)}
    visitadas = {(0, 0)}
    pilha = [(0, 0)]
    while pilha:
        x, y = pilha[-1]
        opcoes = [
            (lado, (x + dx, y + dy))
            for lado, (dx, dy) in DELTA.items()
            if (x + dx, y + dy) in paredes and (x + dx, y + dy) not in visitadas
        ]
        if not opcoes:
            pilha.pop()
            continue
        lado, vizinho = rng.choice(opcoes)
        paredes[(x, y)] &= ~BIT_LADO[lado]
        paredes[vizinho] &= ~BIT_LADO[OPOSTO[lado]]
        visitadas.add(vizinho)
        pilha.append(vizinho)
    return paredes


class NavegacaoSimulada:
    """Explora um labirinto escondido por flood fill; só as células visitadas são reveladas."""

    def __init__(self, largura: int, altura: int, rng: random.Random) -> None:
        self.largura, self.altura = largura, altura
        self._paredes_reais = gerar_labirinto(largura, altura, rng)
        self.objetivo = (largura - 1, altura - 1)
        self.posicao = (0, 0)
        self.direcao = "N"
        self.conhecidas: dict[tuple[int, int], int] = {}
        self.rota: list[tuple[int, int]] = []

    @property
    def chegou(self) -> bool:
        return self.posicao == self.objetivo

    def observar(self) -> Celula:
        paredes = self._paredes_reais[self.posicao]
        self.conhecidas[self.posicao] = paredes
        return Celula(x=self.posicao[0], y=self.posicao[1], walls=paredes, known=15)

    def _bloqueado(self, celula: tuple[int, int], lado: str) -> bool:
        if celula in self.conhecidas:
            return bool(self.conhecidas[celula] & BIT_LADO[lado])
        vizinho = (celula[0] + DELTA[lado][0], celula[1] + DELTA[lado][1])
        if vizinho in self.conhecidas:
            return bool(self.conhecidas[vizinho] & BIT_LADO[OPOSTO[lado]])
        return False

    def planejar(self) -> list[tuple[int, int]]:
        anterior: dict[tuple[int, int], tuple[int, int] | None] = {self.posicao: None}
        fila = deque([self.posicao])
        while fila:
            atual = fila.popleft()
            if atual == self.objetivo:
                break
            for lado, (dx, dy) in DELTA.items():
                vizinho = (atual[0] + dx, atual[1] + dy)
                fora = not (0 <= vizinho[0] < self.largura and 0 <= vizinho[1] < self.altura)
                if fora or vizinho in anterior or self._bloqueado(atual, lado):
                    continue
                anterior[vizinho] = atual
                fila.append(vizinho)
        caminho = []
        celula = self.objetivo if self.objetivo in anterior else None
        while celula is not None:
            caminho.append(celula)
            celula = anterior[celula]
        self.rota = caminho[::-1]
        return self.rota

    def avancar(self) -> bool:
        if len(self.rota) < 2:
            return False
        proxima = self.rota[1]
        passo = (proxima[0] - self.posicao[0], proxima[1] - self.posicao[1])
        self.direcao = next(lado for lado, delta in DELTA.items() if delta == passo)
        self.posicao = proxima
        return True


def perfil_alvo(t_s: float) -> tuple[float, float]:
    fase = t_s % 8.0
    if fase < 3.0:
        return 300.0, 300.0
    if fase < 4.0:
        return 0.0, 0.0
    if fase < 5.0:
        return 150.0, -150.0
    if fase < 6.0:
        return 0.0, 0.0
    return 200.0, 200.0


def _simulada(valor: float | None, unidade: str, valida: bool = True) -> Leitura:
    return Leitura(value=valor, unit=unidade, source="simulated", valid=valida)


class SimuladorRobo:
    def __init__(
        self,
        seed: int = 7,
        robot_id: str = "micromouse-01",
        maze_id: str = "4x4",
        navegacao: bool = False,
        segundos_por_celula: float = 1.0,
    ) -> None:
        if navegacao:
            dimensoes_labirinto(maze_id)
        self._rng = random.Random(seed)
        self.robot_id = robot_id
        self.maze_id = maze_id
        self.navegacao = navegacao
        self.segundos_por_celula = segundos_por_celula
        self._nav: NavegacaoSimulada | None = None
        self._celula_nova = False
        self._rota_valida = False
        self._ultimo_movimento_s = 0.0
        self._amostras_sem_rota = 0
        self.boot_id = f"boot-{self._rng.randrange(16**6):06x}"
        self.run_id: str | None = None
        self._seq = 0
        self._execucoes = 0
        self._inicio_s = 0.0
        self._velocidades = [0.0, 0.0]
        self._bateria_v = 8.2

    def iniciar(self, t_s: float) -> Frame:
        self._execucoes += 1
        self.run_id = f"run-{self._execucoes:03d}"
        self._inicio_s = t_s
        self._velocidades = [0.0, 0.0]
        if self.navegacao:
            largura, altura = dimensoes_labirinto(self.maze_id)
            # Semente própria: o labirinto não muda a sequência aleatória das rodas.
            self._nav = NavegacaoSimulada(largura, altura, random.Random(f"{self.boot_id}/{self.run_id}"))
            self._celula_nova = True
            self._rota_valida = False
            self._ultimo_movimento_s = t_s
        return self._frame(t_s, "start", "executando")

    @property
    def chegou(self) -> bool:
        return self._nav is not None and self._nav.chegou

    def pendentes(self, t_s: float) -> list[Frame]:
        if self._nav is None or not self._celula_nova:
            return []
        self._celula_nova = False
        celula = self._nav.observar()
        self._nav.planejar()
        self._rota_valida = True
        self._amostras_sem_rota = 0
        mapa = AtualizacaoMapa(
            width=self._nav.largura, height=self._nav.altura, source="simulated", cells=[celula]
        )
        return [self._frame(t_s, "map_update", "executando", mapa=mapa, navegacao=self._navegacao(True))]

    def _navegacao(self, com_rota: bool) -> Navegacao | None:
        if self._nav is None:
            return None
        x, y = self._nav.posicao
        rota = None
        if com_rota:
            rota = RotaPlanejada(source="simulated", cells=[Posicao(x=cx, y=cy) for cx, cy in self._nav.rota])
        return Navegacao(
            width=self._nav.largura,
            height=self._nav.altura,
            pose=Pose(x=x, y=y, heading=self._nav.direcao, source="simulated"),
            route=rota,
        )

    def amostra(self, t_s: float, dt_s: float) -> Frame:
        alvos = perfil_alvo(t_s - self._inicio_s)
        ganho = min(1.0, dt_s / 0.25)
        for i, alvo in enumerate(alvos):
            self._velocidades[i] += (alvo - self._velocidades[i]) * ganho + self._rng.gauss(0, 4)
        self._bateria_v = max(6.0, self._bateria_v - 0.0005 * dt_s)

        navegacao = None
        if self._nav is not None:
            if not self._nav.chegou and t_s - self._ultimo_movimento_s >= self.segundos_por_celula:
                self._ultimo_movimento_s = t_s
                if self._nav.avancar():
                    self._celula_nova = True
                    self._rota_valida = False
            self._amostras_sem_rota += 1
            republicar = self._rota_valida and self._amostras_sem_rota >= REPUBLICAR_ROTA
            if republicar:
                self._amostras_sem_rota = 0
            navegacao = self._navegacao(republicar)

        if self._rng.random() < 0.004:
            falha = Falha(code="SENSOR_TIMEOUT", message="Sensor frontal sem resposta")
            sensores = self._sensores(falha_frontal=True)
            return self._frame(t_s, "fault", "executando", alvos, sensores, falha)
        return self._frame(t_s, "sample", "executando", alvos, self._sensores(), navegacao=navegacao)

    def finalizar(self, t_s: float) -> Frame:
        return self._frame(t_s, "finish", "concluido")

    def perder(self, quantidade: int) -> None:
        self._seq += quantidade

    def _sensores(self, falha_frontal: bool = False) -> dict[str, Leitura]:
        sensores = {}
        for nome in SENSORES:
            if nome == "frontal" and falha_frontal:
                sensores[nome] = _simulada(None, "cm", valida=False)
                continue
            sorteio = self._rng.random()
            if sorteio < 0.03:
                sensores[nome] = _simulada(None, "cm")
            else:
                base = 30.0 if nome == "frontal" else 6.0
                sensores[nome] = _simulada(round(base + self._rng.uniform(-3, 3), 1), "cm")
        return sensores

    def _frame(
        self,
        t_s: float,
        evento: str,
        estado: str,
        alvos: tuple[float, float] | None = None,
        sensores: dict[str, Leitura] | None = None,
        falha: Falha | None = None,
        mapa: AtualizacaoMapa | None = None,
        navegacao: Navegacao | None = None,
    ) -> Frame:
        self._seq += 1
        rodas = {}
        erro = None
        if alvos is not None:
            esquerda, direita = self._velocidades
            rodas = {
                "wheel_left": Roda(
                    speed=_simulada(round(esquerda, 1), "mm/s"),
                    target=_simulada(alvos[0], "mm/s"),
                ),
                "wheel_right": Roda(
                    speed=_simulada(round(direita, 1), "mm/s"),
                    target=_simulada(alvos[1], "mm/s"),
                ),
            }
            erro = _simulada(round(((alvos[0] - esquerda) + (alvos[1] - direita)) / 2, 1), "mm/s")
        versao = {"schema_version": 2, "navigation": navegacao} if self.navegacao else {}
        modelo = FrameV2 if self.navegacao else Frame
        return modelo(
            **({"schema_version": VERSAO_CONTRATO} | versao),
            robot_id=self.robot_id,
            boot_id=self.boot_id,
            run_id=self.run_id,
            maze_id=self.maze_id,
            seq=self._seq,
            t_ms=round(t_s * 1000),
            event=evento,
            state=estado,
            control_error=erro,
            sensors=sensores or {},
            battery_voltage=_simulada(round(self._bateria_v, 3), "V"),
            fault=falha,
            map=mapa,
            **rodas,
        )


class FonteSimulada:
    simulada = True
    nome = "simulador"

    def __init__(
        self,
        seed: int = 7,
        taxa_hz: float = 20.0,
        duracao_execucao_s: float = 60.0,
        intervalo_queda_s: float = 25.0,
        duracao_queda_s: float = 4.0,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        navegacao: bool = False,
        maze_id: str = "4x4",
    ) -> None:
        self.seed = seed
        self.dt_s = 1.0 / taxa_hz
        self.duracao_execucao_s = duracao_execucao_s
        self.intervalo_queda_s = intervalo_queda_s
        self.duracao_queda_s = duracao_queda_s
        self._dormir = dormir
        self.navegacao = navegacao
        self.maze_id = maze_id

    async def eventos(self) -> AsyncIterator[Evento]:
        robo = SimuladorRobo(self.seed, maze_id=self.maze_id, navegacao=self.navegacao)
        t_s = 0.0
        proxima_queda = self.intervalo_queda_s
        queda_silenciosa = True
        perdidos = round(self.duracao_queda_s / self.dt_s)
        yield LinkAberto(self.nome)
        while True:
            inicio = t_s
            yield robo.iniciar(t_s)
            for frame in robo.pendentes(t_s):
                yield frame
            while t_s - inicio < self.duracao_execucao_s and not robo.chegou:
                await self._dormir(self.dt_s)
                t_s += self.dt_s
                if t_s >= proxima_queda:
                    proxima_queda += self.intervalo_queda_s
                    if not queda_silenciosa:
                        yield LinkFechado("porta serial desconectada (simulado)")
                    await self._dormir(self.duracao_queda_s)
                    t_s += self.duracao_queda_s
                    robo.perder(perdidos)
                    if not queda_silenciosa:
                        yield LinkAberto(f"{self.nome} (reconectado)")
                    queda_silenciosa = not queda_silenciosa
                    continue
                yield robo.amostra(t_s, self.dt_s)
                for frame in robo.pendentes(t_s):
                    yield frame
            yield robo.finalizar(t_s)
