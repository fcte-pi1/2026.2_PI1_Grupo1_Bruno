"""Persistência SQLite das execuções (TEL03 #19), independente da atualização da UI.

Chaves:
- execução: (robot_id, boot_id, run_id). O contrato proíbe reutilizar run_id no mesmo boot.
- mensagem: (robot_id, boot_id, seq). seq é único por boot, então reenvios viram duplicatas.
"""

import asyncio
import logging
import sqlite3
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from telemetria.formatacao import valor_numerico
from telemetria.modelos import FRAMES_TELEMETRIA, Frame, Leitura

logger = logging.getLogger(__name__)

VERSAO_ESQUEMA = 1
MAX_AMOSTRAS_POR_EXECUCAO = 20_000  # ~33 min a 10 Hz: cobre o ensaio de autonomia de 30 min.
LIMITE_CONSULTA = 100

ESQUEMA = """
CREATE TABLE IF NOT EXISTS execucao (
    id INTEGER PRIMARY KEY,
    robot_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    maze_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('em_andamento', 'concluida', 'incompleta')),
    estado_final TEXT,
    start_recebido INTEGER NOT NULL DEFAULT 0,
    app_interrompido INTEGER NOT NULL DEFAULT 0,
    seq_min INTEGER NOT NULL,
    seq_max INTEGER NOT NULL,
    seq_fim INTEGER,
    t_min_ms INTEGER NOT NULL,
    t_max_ms INTEGER NOT NULL,
    origem_simulada INTEGER NOT NULL DEFAULT 0,
    origem_medida INTEGER NOT NULL DEFAULT 0,
    origem_estimada INTEGER NOT NULL DEFAULT 0,
    falhas INTEGER NOT NULL DEFAULT 0,
    amostras_descartadas INTEGER NOT NULL DEFAULT 0,
    recebido_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    UNIQUE (robot_id, boot_id, run_id)
);
CREATE INDEX IF NOT EXISTS execucao_maze ON execucao (maze_id, recebido_em);
CREATE INDEX IF NOT EXISTS execucao_status ON execucao (status);

CREATE TABLE IF NOT EXISTS amostra (
    id INTEGER PRIMARY KEY,
    execucao_id INTEGER NOT NULL REFERENCES execucao (id) ON DELETE CASCADE,
    robot_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    t_ms INTEGER NOT NULL,
    state TEXT NOT NULL,
    velocidade_esquerda REAL,
    alvo_esquerda REAL,
    velocidade_direita REAL,
    alvo_direita REAL,
    erro_controle REAL,
    tensao_bateria REAL,
    payload TEXT NOT NULL,
    UNIQUE (robot_id, boot_id, seq)
);
CREATE INDEX IF NOT EXISTS amostra_execucao ON amostra (execucao_id, seq);

CREATE TABLE IF NOT EXISTS evento (
    id INTEGER PRIMARY KEY,
    execucao_id INTEGER REFERENCES execucao (id) ON DELETE CASCADE,
    robot_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    run_id TEXT,
    seq INTEGER NOT NULL,
    t_ms INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    state TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (robot_id, boot_id, seq)
);
CREATE INDEX IF NOT EXISTS evento_execucao ON evento (execucao_id, seq);
"""


class Resultado(StrEnum):
    GRAVADO = "gravado"
    DUPLICADO = "duplicado"
    IGNORADO = "ignorado"


@dataclass(frozen=True)
class ResumoExecucao:
    id: int
    robot_id: str
    boot_id: str
    run_id: str
    maze_id: str | None
    status: str
    estado_final: str | None
    start_recebido: bool
    app_interrompido: bool
    duracao_ms: int
    origens: tuple[str, ...]
    falhas: int
    amostras: int
    amostras_descartadas: int
    recebido_em: str


@dataclass(frozen=True)
class AmostraSalva:
    seq: int
    t_ms: int
    state: str
    velocidade_esquerda: float | None
    alvo_esquerda: float | None
    velocidade_direita: float | None
    alvo_direita: float | None


def _agora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def origens(frame: Frame) -> set[str]:
    leituras: list[Leitura | None] = [frame.control_error, frame.battery_voltage, *frame.sensors.values()]
    for roda in (frame.wheel_left, frame.wheel_right):
        if roda is not None:
            leituras += [roda.speed, roda.target]
    encontradas = {leitura.source for leitura in leituras if leitura is not None}
    if frame.map is not None:
        encontradas.add(frame.map.source)
    navegacao = getattr(frame, "navigation", None)
    if navegacao is not None:
        for parte in (navegacao.pose, navegacao.route):
            if parte is not None:
                encontradas.add(parte.source)
    return encontradas


class Armazenamento:
    """Conexão SQLite síncrona. Use sempre a partir de uma única thread."""

    def __init__(
        self,
        caminho: str | Path,
        somente_leitura: bool = False,
        max_amostras_por_execucao: int = MAX_AMOSTRAS_POR_EXECUCAO,
        relogio: Callable[[], str] = _agora,
    ) -> None:
        if max_amostras_por_execucao < 0:
            raise ValueError("max_amostras_por_execucao não pode ser negativo")
        self.caminho = Path(caminho)
        self.somente_leitura = somente_leitura
        self.max_amostras_por_execucao = max_amostras_por_execucao
        self._relogio = relogio
        self._conexao: sqlite3.Connection | None = None

    def abrir(self) -> None:
        if self._conexao is not None:
            return
        if self.somente_leitura:
            conexao = sqlite3.connect(f"{self.caminho.resolve().as_uri()}?mode=ro", uri=True)
        else:
            conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("PRAGMA busy_timeout = 5000")
        self._conexao = conexao
        if self.somente_leitura:
            return
        conexao.execute("PRAGMA journal_mode = WAL")
        versao = conexao.execute("PRAGMA user_version").fetchone()[0]
        if versao not in (0, VERSAO_ESQUEMA):
            conexao.close()
            self._conexao = None
            raise RuntimeError(f"banco com esquema v{versao}; esta versão entende v{VERSAO_ESQUEMA}")
        with conexao:
            conexao.executescript(ESQUEMA)
            conexao.execute(f"PRAGMA user_version = {VERSAO_ESQUEMA}")
        # O app anterior caiu ou fechou com corridas abertas: os dados delas podem ter lacunas.
        interrompidas = self._marcar_interrompidas()
        if interrompidas:
            logger.warning("%d execução(ões) sem finish marcadas como incompletas", interrompidas)

    def fechar(self) -> None:
        if self._conexao is None:
            return
        if not self.somente_leitura:
            self._marcar_interrompidas()
        self._conexao.close()
        self._conexao = None

    def __enter__(self) -> "Armazenamento":
        self.abrir()
        return self

    def __exit__(self, *_: object) -> None:
        self.fechar()

    @property
    def conexao(self) -> sqlite3.Connection:
        if self._conexao is None:
            raise RuntimeError("armazenamento não está aberto")
        return self._conexao

    def _marcar_interrompidas(self) -> int:
        with self.conexao:
            cursor = self.conexao.execute(
                "UPDATE execucao SET status = 'incompleta', app_interrompido = 1, atualizado_em = ? "
                "WHERE status = 'em_andamento'",
                (self._relogio(),),
            )
        return cursor.rowcount

    def registrar(self, frame: Frame) -> Resultado:
        return self.registrar_lote([frame])[0]

    def registrar_lote(self, frames: Iterable[Frame]) -> list[Resultado]:
        """Grava os frames em uma transação; reenvios do mesmo (robot, boot, seq) são ignorados."""
        with self.conexao:
            return [self._registrar(frame) for frame in frames]

    def _registrar(self, frame: Frame) -> Resultado:
        if self._ja_gravado(frame):
            return Resultado.DUPLICADO
        if frame.run_id is None:
            # Fora de corrida só interessam falhas; snapshots de "pronto" não pertencem ao histórico.
            if frame.event != "fault":
                return Resultado.IGNORADO
            self._inserir_evento(frame, None)
            return Resultado.GRAVADO

        execucao = self._execucao(frame)
        encerrada = execucao is not None and execucao["seq_fim"] is not None
        # finish é terminal: outro finish ou mensagem posterior não altera a execução.
        if encerrada and (frame.event == "finish" or frame.seq > execucao["seq_fim"]):
            return Resultado.IGNORADO
        execucao_id = self._atualizar_execucao(frame, execucao)

        if frame.event == "sample":
            total = self.conexao.execute(
                "SELECT COUNT(*) FROM amostra WHERE execucao_id = ?", (execucao_id,)
            ).fetchone()[0]
            if total >= self.max_amostras_por_execucao:
                self.conexao.execute(
                    "UPDATE execucao SET amostras_descartadas = amostras_descartadas + 1 WHERE id = ?",
                    (execucao_id,),
                )
                return Resultado.IGNORADO
            self._inserir_amostra(frame, execucao_id)
        else:
            self._inserir_evento(frame, execucao_id)
        return Resultado.GRAVADO

    def _ja_gravado(self, frame: Frame) -> bool:
        chave = (frame.robot_id, frame.boot_id, frame.seq)
        consulta = "SELECT 1 FROM {} WHERE robot_id = ? AND boot_id = ? AND seq = ?"
        return any(
            self.conexao.execute(consulta.format(tabela), chave).fetchone()
            for tabela in ("amostra", "evento")
        )

    def _execucao(self, frame: Frame) -> sqlite3.Row | None:
        return self.conexao.execute(
            "SELECT * FROM execucao WHERE robot_id = ? AND boot_id = ? AND run_id = ?",
            (frame.robot_id, frame.boot_id, frame.run_id),
        ).fetchone()

    def _atualizar_execucao(self, frame: Frame, execucao: sqlite3.Row | None) -> int:
        agora = self._relogio()
        fontes = origens(frame)
        flags = (
            int("simulated" in fontes),
            int("measured" in fontes),
            int("estimated" in fontes),
        )
        fim = frame.event == "finish"
        if execucao is None:
            cursor = self.conexao.execute(
                "INSERT INTO execucao (robot_id, boot_id, run_id, maze_id, status, estado_final, "
                "start_recebido, seq_min, seq_max, seq_fim, t_min_ms, t_max_ms, origem_simulada, "
                "origem_medida, origem_estimada, falhas, recebido_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    frame.robot_id,
                    frame.boot_id,
                    frame.run_id,
                    frame.maze_id,
                    "concluida" if fim else "em_andamento",
                    frame.state if fim else None,
                    int(frame.event == "start"),
                    frame.seq,
                    frame.seq,
                    frame.seq if fim else None,
                    frame.t_ms,
                    frame.t_ms,
                    *flags,
                    int(frame.event == "fault"),
                    agora,
                    agora,
                ),
            )
            return cursor.lastrowid

        status = "concluida" if fim else ("em_andamento" if execucao["status"] == "incompleta" else None)
        self.conexao.execute(
            "UPDATE execucao SET "
            "maze_id = COALESCE(maze_id, ?), "
            "status = COALESCE(?, status), "
            "estado_final = COALESCE(?, estado_final), "
            "start_recebido = MAX(start_recebido, ?), "
            "seq_min = MIN(seq_min, ?), seq_max = MAX(seq_max, ?), "
            "seq_fim = COALESCE(?, seq_fim), "
            "t_min_ms = MIN(t_min_ms, ?), t_max_ms = MAX(t_max_ms, ?), "
            "origem_simulada = MAX(origem_simulada, ?), "
            "origem_medida = MAX(origem_medida, ?), "
            "origem_estimada = MAX(origem_estimada, ?), "
            "falhas = falhas + ?, "
            "atualizado_em = ? "
            "WHERE id = ?",
            (
                frame.maze_id,
                status,
                frame.state if fim else None,
                int(frame.event == "start"),
                frame.seq,
                frame.seq,
                frame.seq if fim else None,
                frame.t_ms,
                frame.t_ms,
                *flags,
                int(frame.event == "fault"),
                agora,
                execucao["id"],
            ),
        )
        return execucao["id"]

    def _inserir_amostra(self, frame: Frame, execucao_id: int) -> None:
        esquerda, direita = frame.wheel_left, frame.wheel_right
        self.conexao.execute(
            "INSERT INTO amostra (execucao_id, robot_id, boot_id, seq, t_ms, state, velocidade_esquerda, "
            "alvo_esquerda, velocidade_direita, alvo_direita, erro_controle, tensao_bateria, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                execucao_id,
                frame.robot_id,
                frame.boot_id,
                frame.seq,
                frame.t_ms,
                frame.state,
                valor_numerico(esquerda.speed if esquerda else None),
                valor_numerico(esquerda.target if esquerda else None),
                valor_numerico(direita.speed if direita else None),
                valor_numerico(direita.target if direita else None),
                valor_numerico(frame.control_error),
                valor_numerico(frame.battery_voltage),
                frame.model_dump_json(exclude_none=True),
            ),
        )

    def _inserir_evento(self, frame: Frame, execucao_id: int | None) -> None:
        self.conexao.execute(
            "INSERT INTO evento (execucao_id, robot_id, boot_id, run_id, seq, t_ms, tipo, state, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                execucao_id,
                frame.robot_id,
                frame.boot_id,
                frame.run_id,
                frame.seq,
                frame.t_ms,
                frame.event,
                frame.state,
                frame.model_dump_json(exclude_none=True),
            ),
        )

    def execucoes(
        self,
        maze_id: str | None = None,
        status: str | None = None,
        origem: str | None = None,
        limite: int = LIMITE_CONSULTA,
        deslocamento: int = 0,
    ) -> list[ResumoExecucao]:
        """Histórico geral ou filtrado, da execução recebida mais recentemente para a mais antiga."""
        if not 1 <= limite <= LIMITE_CONSULTA or deslocamento < 0:
            raise ValueError(f"limite deve estar entre 1 e {LIMITE_CONSULTA}; deslocamento não negativo")
        coluna_origem = {
            "simulated": "origem_simulada",
            "measured": "origem_medida",
            "estimated": "origem_estimada",
        }
        if origem is not None and origem not in coluna_origem:
            raise ValueError("origem deve ser simulated, measured ou estimated")
        filtros, parametros = [], []
        if maze_id is not None:
            filtros.append("e.maze_id = ?")
            parametros.append(maze_id)
        if status is not None:
            filtros.append("e.status = ?")
            parametros.append(status)
        if origem is not None:
            filtros.append(f"e.{coluna_origem[origem]} = 1")
        onde = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        linhas = self.conexao.execute(
            "SELECT e.*, (SELECT COUNT(*) FROM amostra a WHERE a.execucao_id = e.id) AS total_amostras "
            f"FROM execucao e {onde} ORDER BY e.recebido_em DESC, e.id DESC LIMIT ? OFFSET ?",
            (*parametros, limite, deslocamento),
        ).fetchall()
        return [self._resumo(linha) for linha in linhas]

    def labirintos(self) -> list[str]:
        linhas = self.conexao.execute(
            "SELECT DISTINCT maze_id FROM execucao WHERE maze_id IS NOT NULL ORDER BY maze_id"
        ).fetchall()
        return [linha[0] for linha in linhas]

    def amostras(self, execucao_id: int) -> list[AmostraSalva]:
        linhas = self.conexao.execute(
            "SELECT seq, t_ms, state, velocidade_esquerda, alvo_esquerda, velocidade_direita, alvo_direita "
            "FROM amostra WHERE execucao_id = ? ORDER BY seq",
            (execucao_id,),
        ).fetchall()
        return [AmostraSalva(**dict(linha)) for linha in linhas]

    def eventos(self, execucao_id: int | None) -> list[Frame]:
        """Eventos na ordem do robô (seq); None devolve falhas registradas fora de corrida."""
        condicao = "execucao_id IS NULL" if execucao_id is None else "execucao_id = ?"
        linhas = self.conexao.execute(
            f"SELECT payload FROM evento WHERE {condicao} ORDER BY boot_id, seq",
            () if execucao_id is None else (execucao_id,),
        ).fetchall()
        return [FRAMES_TELEMETRIA.validate_json(linha[0]) for linha in linhas]

    def frames(self, execucao_id: int) -> list[Frame]:
        """Amostras e eventos da execução, na ordem de seq, para o replay."""
        linhas = self.conexao.execute(
            "SELECT seq, payload FROM amostra WHERE execucao_id = ? "
            "UNION ALL SELECT seq, payload FROM evento WHERE execucao_id = ? ORDER BY seq",
            (execucao_id, execucao_id),
        ).fetchall()
        return [FRAMES_TELEMETRIA.validate_json(linha[1]) for linha in linhas]

    def execucao(self, execucao_id: int) -> ResumoExecucao | None:
        linha = self.conexao.execute(
            "SELECT e.*, (SELECT COUNT(*) FROM amostra a WHERE a.execucao_id = e.id) AS total_amostras "
            "FROM execucao e WHERE e.id = ?",
            (execucao_id,),
        ).fetchone()
        return None if linha is None else self._resumo(linha)

    def podar_amostras(self, manter_execucoes: int) -> int:
        """Retenção: apaga amostras de execuções antigas; resumo e eventos permanecem."""
        if manter_execucoes < 0:
            raise ValueError("manter_execucoes não pode ser negativo")
        with self.conexao:
            cursor = self.conexao.execute(
                "DELETE FROM amostra WHERE execucao_id NOT IN "
                "(SELECT id FROM execucao ORDER BY recebido_em DESC, id DESC LIMIT ?)",
                (manter_execucoes,),
            )
        return cursor.rowcount

    @staticmethod
    def _resumo(linha: sqlite3.Row) -> ResumoExecucao:
        fontes = (
            ("simulated", linha["origem_simulada"]),
            ("measured", linha["origem_medida"]),
            ("estimated", linha["origem_estimada"]),
        )
        return ResumoExecucao(
            id=linha["id"],
            robot_id=linha["robot_id"],
            boot_id=linha["boot_id"],
            run_id=linha["run_id"],
            maze_id=linha["maze_id"],
            status=linha["status"],
            estado_final=linha["estado_final"],
            start_recebido=bool(linha["start_recebido"]),
            app_interrompido=bool(linha["app_interrompido"]),
            duracao_ms=linha["t_max_ms"] - linha["t_min_ms"],
            origens=tuple(nome for nome, presente in fontes if presente),
            falhas=linha["falhas"],
            amostras=linha["total_amostras"],
            amostras_descartadas=linha["amostras_descartadas"],
            recebido_em=linha["recebido_em"],
        )


class GravadorAssincrono:
    """Fila limitada + thread única do SQLite: gravar não depende do refresh da interface.

    Fila cheia aplica backpressure à coleta em vez de perder start/finish/fault em silêncio.
    Erro de disco é registrado e a coleta continua; os frames daquele lote ficam fora do banco.
    """

    def __init__(self, armazenamento: Armazenamento, fila_max: int = 1000, lote_max: int = 100) -> None:
        if fila_max < 1 or lote_max < 1:
            raise ValueError("fila_max e lote_max devem ser positivos")
        self.armazenamento = armazenamento
        self.lote_max = lote_max
        self.falhas_gravacao = 0
        self._fila: asyncio.Queue[Frame | None] = asyncio.Queue(fila_max)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sqlite")
        self._tarefa: asyncio.Task[None] | None = None

    async def _na_thread(self, funcao: Callable[..., object], *args: object) -> object:
        return await asyncio.get_running_loop().run_in_executor(self._executor, funcao, *args)

    async def iniciar(self) -> None:
        if self._tarefa is None:
            await self._na_thread(self.armazenamento.abrir)
            self._tarefa = asyncio.create_task(self._consumir(), name="gravador-sqlite")

    async def gravar(self, frame: Frame) -> None:
        if self._tarefa is None:
            raise RuntimeError("gravador não iniciado")
        await self._fila.put(frame)

    async def _consumir(self) -> None:
        while True:
            primeiro = await self._fila.get()
            lote = [] if primeiro is None else [primeiro]
            encerrar = primeiro is None
            while not encerrar and len(lote) < self.lote_max and not self._fila.empty():
                proximo = self._fila.get_nowait()
                if proximo is None:
                    encerrar = True
                else:
                    lote.append(proximo)
            if lote:
                try:
                    await self._na_thread(self.armazenamento.registrar_lote, lote)
                except sqlite3.Error:
                    self.falhas_gravacao += 1
                    logger.exception("falha ao gravar %d frame(s); recepção continua", len(lote))
            if encerrar:
                return

    async def fechar(self) -> None:
        """Grava o que já está na fila antes de fechar o banco."""
        if self._tarefa is not None:
            await self._fila.put(None)
            await asyncio.gather(self._tarefa, return_exceptions=True)
            self._tarefa = None
        try:
            await self._na_thread(self.armazenamento.fechar)
        finally:
            self._executor.shutdown(wait=True)
