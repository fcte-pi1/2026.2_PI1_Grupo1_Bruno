import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable

from telemetria.modelos import (
    VERSAO_CONTRATO,
    Evento,
    Falha,
    Frame,
    Leitura,
    LinkAberto,
    LinkFechado,
    Roda,
)

SENSORES = ("frontal", "esquerda", "direita")


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
    def __init__(self, seed: int = 7, robot_id: str = "micromouse-01", maze_id: str = "4x4") -> None:
        self._rng = random.Random(seed)
        self.robot_id = robot_id
        self.maze_id = maze_id
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
        return self._frame(t_s, "start", "executando")

    def amostra(self, t_s: float, dt_s: float) -> Frame:
        alvos = perfil_alvo(t_s - self._inicio_s)
        ganho = min(1.0, dt_s / 0.25)
        for i, alvo in enumerate(alvos):
            self._velocidades[i] += (alvo - self._velocidades[i]) * ganho + self._rng.gauss(0, 4)
        self._bateria_v = max(6.0, self._bateria_v - 0.0005 * dt_s)

        if self._rng.random() < 0.004:
            falha = Falha(code="SENSOR_TIMEOUT", message="Sensor frontal sem resposta")
            sensores = self._sensores(falha_frontal=True)
            return self._frame(t_s, "fault", "executando", alvos, sensores, falha)
        return self._frame(t_s, "sample", "executando", alvos, self._sensores())

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
        return Frame(
            schema_version=VERSAO_CONTRATO,
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
    ) -> None:
        self.seed = seed
        self.dt_s = 1.0 / taxa_hz
        self.duracao_execucao_s = duracao_execucao_s
        self.intervalo_queda_s = intervalo_queda_s
        self.duracao_queda_s = duracao_queda_s
        self._dormir = dormir

    async def eventos(self) -> AsyncIterator[Evento]:
        robo = SimuladorRobo(self.seed)
        t_s = 0.0
        proxima_queda = self.intervalo_queda_s
        queda_silenciosa = True
        perdidos = round(self.duracao_queda_s / self.dt_s)
        yield LinkAberto(self.nome)
        while True:
            inicio = t_s
            yield robo.iniciar(t_s)
            while t_s - inicio < self.duracao_execucao_s:
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
            yield robo.finalizar(t_s)
