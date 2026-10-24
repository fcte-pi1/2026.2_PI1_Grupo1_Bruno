import pytest

from telemetria.modelos import VERSAO_CONTRATO, Falha, Frame, Leitura, Roda


class Relogio:
    def __init__(self) -> None:
        self.agora = 100.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


@pytest.fixture
def relogio() -> Relogio:
    return Relogio()


def leitura(
    valor: float | None, unidade: str = "mm/s", origem: str = "measured", valida: bool = True
) -> Leitura:
    return Leitura(value=valor, unit=unidade, source=origem, valid=valida)


def criar_frame(
    seq: int,
    t_ms: int | None = None,
    boot_id: str = "boot-a",
    run_id: str | None = "run-001",
    evento: str = "sample",
    velocidade_esquerda: float | None = 100.0,
    falha: Falha | None = None,
) -> Frame:
    return Frame(
        schema_version=VERSAO_CONTRATO,
        robot_id="micromouse-01",
        boot_id=boot_id,
        run_id=run_id,
        maze_id="4x4",
        seq=seq,
        t_ms=seq * 50 if t_ms is None else t_ms,
        event=evento,
        state="executando",
        wheel_left=Roda(speed=leitura(velocidade_esquerda), target=leitura(120.0)),
        wheel_right=Roda(speed=leitura(98.0), target=leitura(120.0)),
        control_error=leitura(11.0, origem="estimated"),
        sensors={"frontal": leitura(30.0, "cm")},
        battery_voltage=leitura(8.1, "V"),
        fault=falha,
    )
