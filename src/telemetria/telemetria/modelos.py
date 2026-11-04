from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

VERSAO_CONTRATO = 1
MAX_FRAME_BYTES = 4096  # utf-8, sem lf
TAXA_INICIAL_HZ = 10
MAX_INTEIRO = 2**53 - 1

Origem = Literal["simulated", "measured", "estimated"]
TipoEvento = Literal["start", "sample", "map_update", "fault", "finish"]


class ModeloContrato(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class Leitura(ModeloContrato):
    value: float | None = None
    unit: Literal["mm/s", "cm", "V"]
    source: Origem
    valid: bool = True


class Roda(ModeloContrato):
    speed: Leitura
    target: Leitura

    @model_validator(mode="after")
    def unidades(self) -> "Roda":
        if self.speed.unit != "mm/s" or self.target.unit != "mm/s":
            raise ValueError("velocidades devem usar mm/s")
        return self


class Falha(ModeloContrato):
    code: str = Field(min_length=1, max_length=40)
    message: str = Field(max_length=200)


class Celula(ModeloContrato):
    x: int = Field(ge=0, le=31)
    y: int = Field(ge=0, le=31)
    walls: int = Field(ge=0, le=15)
    known: int = Field(ge=0, le=15)

    @model_validator(mode="after")
    def paredes_conhecidas(self) -> "Celula":
        if self.walls & ~self.known:
            raise ValueError("walls deve ser subconjunto de known")
        return self


class AtualizacaoMapa(ModeloContrato):
    width: int = Field(ge=1, le=32)
    height: int = Field(ge=1, le=32)
    source: Origem
    cells: list[Celula] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def coordenadas(self) -> "AtualizacaoMapa":
        vistas = set()
        for celula in self.cells:
            chave = (celula.x, celula.y)
            if celula.x >= self.width or celula.y >= self.height or chave in vistas:
                raise ValueError("célula fora do mapa ou repetida")
            vistas.add(chave)
        return self


class EstatisticasTelemetria(ModeloContrato):
    control_cycles: int = Field(ge=0, le=MAX_INTEIRO)
    control_late_cycles: int = Field(ge=0, le=MAX_INTEIRO)
    samples_dropped: int = Field(ge=0, le=MAX_INTEIRO)
    events_dropped: int = Field(ge=0, le=MAX_INTEIRO)
    queue_high_water: int = Field(ge=0, le=MAX_INTEIRO)


class Versionado(ModeloContrato):
    schema_version: Literal[1]

    @field_validator("schema_version", mode="before")
    @classmethod
    def versao_inteira(cls, valor: object) -> object:
        if type(valor) is not int:
            raise ValueError("schema_version deve ser inteiro JSON")
        return valor


class Frame(Versionado):
    robot_id: str = Field(min_length=1, max_length=40)
    boot_id: str = Field(min_length=1, max_length=40)
    run_id: str | None = Field(default=None, min_length=1, max_length=40)
    maze_id: str | None = Field(default=None, min_length=1, max_length=20)
    seq: int = Field(ge=0, le=MAX_INTEIRO)
    t_ms: int = Field(ge=0, le=MAX_INTEIRO)
    event: TipoEvento
    state: str = Field(min_length=1, max_length=30)
    wheel_left: Roda | None = None
    wheel_right: Roda | None = None
    control_error: Leitura | None = None
    sensors: dict[str, Leitura] = Field(default_factory=dict, max_length=8)
    battery_voltage: Leitura | None = None
    fault: Falha | None = None
    map: AtualizacaoMapa | None = None
    telemetry_stats: EstatisticasTelemetria | None = None

    @model_validator(mode="after")
    def coerencia(self) -> "Frame":
        if self.event in {"start", "finish"} and self.run_id is None:
            raise ValueError("start/finish exigem run_id")
        if (self.event == "fault") != (self.fault is not None):
            raise ValueError("fault deve existir somente no evento fault")
        if (self.event == "map_update") != (self.map is not None):
            raise ValueError("map deve existir somente no evento map_update")
        if self.map is not None and self.maze_id is None:
            raise ValueError("map_update exige maze_id")
        if self.control_error is not None and self.control_error.unit != "mm/s":
            raise ValueError("control_error deve usar mm/s")
        if self.battery_voltage is not None and self.battery_voltage.unit != "V":
            raise ValueError("battery_voltage deve usar V")
        if any(not 1 <= len(nome) <= 24 or leitura.unit != "cm" for nome, leitura in self.sensors.items()):
            raise ValueError("sensores exigem nome de 1..24 caracteres e unidade cm")
        return self


class Posicao(ModeloContrato):
    x: int = Field(ge=0, le=31)
    y: int = Field(ge=0, le=31)


class Pose(Posicao):
    heading: Literal["N", "E", "S", "W"]
    source: Origem


class RotaPlanejada(ModeloContrato):
    source: Origem
    cells: list[Posicao] = Field(max_length=1024)

    @model_validator(mode="after")
    def continuidade(self) -> "RotaPlanejada":
        for anterior, atual in zip(self.cells, self.cells[1:], strict=False):
            if abs(anterior.x - atual.x) + abs(anterior.y - atual.y) != 1:
                raise ValueError("rota exige células consecutivas vizinhas por uma face")
        return self


class Navegacao(ModeloContrato):
    width: int = Field(ge=1, le=32)
    height: int = Field(ge=1, le=32)
    pose: Pose | None = None
    route: RotaPlanejada | None = None

    @model_validator(mode="after")
    def coordenadas(self) -> "Navegacao":
        if self.pose is None and self.route is None:
            raise ValueError("navigation exige pose ou route")
        posicoes = ([self.pose] if self.pose is not None else []) + (self.route.cells if self.route else [])
        if any(posicao.x >= self.width or posicao.y >= self.height for posicao in posicoes):
            raise ValueError("posição fora do mapa de navegação")
        if self.pose is not None and self.route is not None and self.route.cells:
            inicio = self.route.cells[0]
            if (inicio.x, inicio.y) != (self.pose.x, self.pose.y):
                raise ValueError("rota deve começar na pose do mesmo snapshot")
        return self


class FrameV2(Frame):
    schema_version: Literal[2]
    navigation: Navegacao | None = None

    @model_validator(mode="after")
    def contexto_navegacao(self) -> "FrameV2":
        if self.navigation is not None:
            if self.maze_id is None:
                raise ValueError("navigation exige maze_id")
            if self.map is not None and (self.map.width, self.map.height) != (
                self.navigation.width,
                self.navigation.height,
            ):
                raise ValueError("map e navigation exigem as mesmas dimensões")
        return self


FRAMES_TELEMETRIA = TypeAdapter(Frame | FrameV2)


class Comando(Versionado):
    kind: Literal["command"]
    robot_id: str = Field(min_length=1, max_length=40)
    boot_id: str = Field(min_length=1, max_length=40)
    run_id: str | None = Field(min_length=1, max_length=40)
    command_id: str = Field(min_length=1, max_length=40)
    command: Literal["ping", "stop", "start"]
    expires_at_ms: int = Field(ge=0, le=MAX_INTEIRO)


class Ack(Versionado):
    kind: Literal["ack"]
    robot_id: str = Field(min_length=1, max_length=40)
    boot_id: str = Field(min_length=1, max_length=40)
    run_id: str | None = Field(min_length=1, max_length=40)
    command_id: str = Field(min_length=1, max_length=40)
    status: Literal["ok", "error"]
    error: (
        Literal["wrong_target", "expired", "invalid_state", "remote_start_disabled", "id_conflict", "busy"]
        | None
    )
    state: str = Field(min_length=1, max_length=30)
    t_ms: int = Field(ge=0, le=MAX_INTEIRO)

    @model_validator(mode="after")
    def resultado(self) -> "Ack":
        if (self.status == "error") != (self.error is not None):
            raise ValueError("ACK error exige código; ACK ok exige error=null")
        return self


@dataclass(frozen=True)
class LinkAberto:
    descricao: str


@dataclass(frozen=True)
class LinkFechado:
    motivo: str


Evento = Frame | LinkAberto | LinkFechado
