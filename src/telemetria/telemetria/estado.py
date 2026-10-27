import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from telemetria.formatacao import valor_numerico
from telemetria.mapa import EstadoMapa
from telemetria.modelos import Frame


class Conexao(StrEnum):
    AGUARDANDO = "aguardando"
    CONECTADO = "conectado"
    DESATUALIZADO = "desatualizado"
    DESCONECTADO = "desconectado"


@dataclass(frozen=True)
class Amostra:
    t_s: float
    esquerda: float | None
    alvo_esquerda: float | None
    direita: float | None
    alvo_direita: float | None


@dataclass(frozen=True)
class RegistroLog:
    numero: int
    instante: datetime
    nivel: str
    texto: str


class EstadoPainel:
    def __init__(
        self,
        limite_desatualizado_s: float = 2.0,
        limite_desconectado_s: float = 5.0,
        janela_s: float = 30.0,
        max_amostras: int = 2000,
        max_log: int = 200,
        relogio: Callable[[], float] = time.monotonic,
        max_epocas: int = 256,
    ) -> None:
        if max_epocas < 1:
            raise ValueError("max_epocas deve ser positivo")
        self.limite_desatualizado_s = limite_desatualizado_s
        self.limite_desconectado_s = limite_desconectado_s
        self.janela_s = janela_s
        self._relogio = relogio
        self.ultimo_frame: Frame | None = None
        self.mapa = EstadoMapa()
        self.amostras: deque[Amostra] = deque(maxlen=max_amostras)
        self.log: deque[RegistroLog] = deque(maxlen=max_log)
        self.descartados = 0
        self.versao = 0
        self._ultimo_rx: float | None = None
        self._link_ativo = False
        self._contador_log = 0
        self._max_epocas = max_epocas
        self._boots_encerrados: set[str] = set()
        self._runs_encerrados: set[str] = set()

    def conexao(self) -> Conexao:
        if not self._link_ativo:
            return Conexao.AGUARDANDO if self._ultimo_rx is None else Conexao.DESCONECTADO
        if self._ultimo_rx is None:
            return Conexao.AGUARDANDO
        idade = self._relogio() - self._ultimo_rx
        if idade <= self.limite_desatualizado_s:
            return Conexao.CONECTADO
        if idade <= self.limite_desconectado_s:
            return Conexao.DESATUALIZADO
        return Conexao.DESCONECTADO

    def segundos_desde_ultima_mensagem(self) -> float | None:
        if self._ultimo_rx is None:
            return None
        return self._relogio() - self._ultimo_rx

    def link_aberto(self, descricao: str) -> None:
        self._link_ativo = True
        self._registrar_log("info", f"Conexão aberta: {descricao}")

    def link_fechado(self, motivo: str) -> None:
        self._link_ativo = False
        self._registrar_log("aviso", f"Conexão perdida: {motivo}")

    def registrar(self, frame: Frame) -> bool:
        anterior = self.ultimo_frame
        novo_boot = anterior is not None and frame.boot_id != anterior.boot_id
        novo_run = anterior is not None and frame.run_id != anterior.run_id
        if anterior is not None:
            invalido = frame.robot_id != anterior.robot_id
            if novo_boot:
                invalido |= frame.boot_id in self._boots_encerrados
                invalido |= len(self._boots_encerrados) >= self._max_epocas
            else:
                invalido |= frame.seq <= anterior.seq or frame.t_ms < anterior.t_ms
                invalido |= anterior.event == "finish" and frame.run_id == anterior.run_id
                if novo_run:
                    invalido |= frame.run_id is not None and frame.run_id in self._runs_encerrados
                    invalido |= anterior.run_id is not None and len(self._runs_encerrados) >= self._max_epocas
            if invalido:
                self.descartados += 1
                self.versao += 1
                return False

        if novo_boot:
            self._boots_encerrados.add(anterior.boot_id)
            self._runs_encerrados.clear()
            self._registrar_log("aviso", f"Novo boot do robô detectado ({frame.boot_id})")
        elif novo_run and anterior.run_id is not None:
            self._runs_encerrados.add(anterior.run_id)

        if novo_boot or novo_run:
            self.amostras.clear()

        self._link_ativo = True
        self._ultimo_rx = self._relogio()
        self.ultimo_frame = frame
        self._guardar_amostra(frame)
        self._registrar_evento(frame)
        self.mapa.aplicar(frame)
        self.versao += 1
        return True

    def amostras_na_janela(self) -> list[Amostra]:
        return list(self.amostras)

    def _guardar_amostra(self, frame: Frame) -> None:
        esquerda = frame.wheel_left
        direita = frame.wheel_right
        t_s = frame.t_ms / 1000
        self.amostras.append(
            Amostra(
                t_s=t_s,
                esquerda=valor_numerico(esquerda.speed if esquerda else None),
                alvo_esquerda=valor_numerico(esquerda.target if esquerda else None),
                direita=valor_numerico(direita.speed if direita else None),
                alvo_direita=valor_numerico(direita.target if direita else None),
            )
        )
        while self.amostras and self.amostras[0].t_s < t_s - self.janela_s:
            self.amostras.popleft()

    def _registrar_evento(self, frame: Frame) -> None:
        if frame.event == "start":
            self._registrar_log("info", f"Execução iniciada: {frame.run_id} (labirinto {frame.maze_id})")
        elif frame.event == "finish":
            self._registrar_log("info", f"Execução encerrada: {frame.run_id} ({frame.state})")
        elif frame.event == "fault":
            if frame.fault is not None:
                texto = f"Falha {frame.fault.code}: {frame.fault.message}"
            else:
                texto = "Falha sem descrição"
            self._registrar_log("erro", texto)

    def _registrar_log(self, nivel: str, texto: str) -> None:
        self._contador_log += 1
        self.log.append(RegistroLog(self._contador_log, datetime.now(), nivel, texto))
        self.versao += 1
