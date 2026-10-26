from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VERSAO_CONTRATO = 1

Origem = Literal["simulated", "measured", "estimated"]
TipoEvento = Literal["start", "sample", "fault", "finish"]


class Leitura(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float | None = None
    unit: str = Field(min_length=1, max_length=16)
    source: Origem
    valid: bool = True


class Roda(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    speed: Leitura
    target: Leitura


class Falha(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=40)
    message: str = Field(max_length=200)


class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    robot_id: str = Field(min_length=1, max_length=40)
    boot_id: str = Field(min_length=1, max_length=40)
    run_id: str | None = Field(default=None, max_length=40)
    maze_id: str | None = Field(default=None, max_length=20)
    seq: int = Field(ge=0)
    t_ms: int = Field(ge=0)
    event: TipoEvento
    state: str = Field(min_length=1, max_length=30)
    wheel_left: Roda | None = None
    wheel_right: Roda | None = None
    control_error: Leitura | None = None
    sensors: dict[str, Leitura] = Field(default_factory=dict)
    battery_voltage: Leitura | None = None
    fault: Falha | None = None


@dataclass(frozen=True)
class LinkAberto:
    descricao: str


@dataclass(frozen=True)
class LinkFechado:
    motivo: str


Evento = Frame | LinkAberto | LinkFechado
