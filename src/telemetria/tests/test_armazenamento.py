import sqlite3

import pytest
from conftest import criar_frame

from telemetria.armazenamento import Armazenamento, GravadorAssincrono, Resultado, origens
from telemetria.gerador import gerar_frames
from telemetria.modelos import Falha


def frame(seq: int, evento: str = "sample", run_id: str | None = "run-001", **mudancas):
    falha = Falha(code="SENSOR_TIMEOUT", message="sem resposta") if evento == "fault" else None
    base = criar_frame(seq, evento=evento, run_id=run_id, falha=falha)
    return base.model_copy(update=mudancas) if mudancas else base


def corrida(run_id: str = "run-001", inicio: int = 1, amostras: int = 3, boot_id: str = "boot-a"):
    seqs = range(inicio, inicio + amostras + 2)
    eventos = ["start", *["sample"] * amostras, "finish"]
    return [frame(s, e, run_id, boot_id=boot_id) for s, e in zip(seqs, eventos, strict=True)]


@pytest.fixture
def banco(tmp_path):
    with Armazenamento(tmp_path / "telemetria.db") as armazenamento:
        yield armazenamento


def test_execucao_completa_do_gerador(banco):
    frames = list(gerar_frames(duracao_s=1.0))
    resultados = banco.registrar_lote(frames)
    assert set(resultados) == {Resultado.GRAVADO}

    [resumo] = banco.execucoes()
    assert resumo.status == "concluida"
    assert resumo.estado_final == "concluido"
    assert resumo.maze_id == "4x4"
    assert resumo.start_recebido and not resumo.app_interrompido
    assert resumo.duracao_ms == 1000
    assert resumo.origens == ("simulated",)
    amostras = sum(f.event == "sample" for f in frames)
    assert resumo.amostras == amostras
    assert [e.event for e in banco.eventos(resumo.id)][0] == "start"
    assert [e.event for e in banco.eventos(resumo.id)][-1] == "finish"


def test_reenvio_do_mesmo_frame_nao_duplica(banco):
    frames = corrida()
    banco.registrar_lote(frames)
    assert set(banco.registrar_lote(frames)) == {Resultado.DUPLICADO}
    [resumo] = banco.execucoes()
    assert resumo.amostras == 3
    assert len(banco.eventos(resumo.id)) == 2


def test_finish_repetido_com_outro_seq_nao_altera_execucao(banco):
    banco.registrar_lote(corrida())
    segundo_finish = frame(10, "finish", state="parado")
    assert banco.registrar(segundo_finish) == Resultado.IGNORADO
    assert banco.registrar(frame(11)) == Resultado.IGNORADO
    [resumo] = banco.execucoes()
    assert resumo.estado_final == "executando"  # state do primeiro finish
    assert [e.event for e in banco.eventos(resumo.id)].count("finish") == 1
    assert resumo.amostras == 3


def test_duas_execucoes_do_mesmo_boot_ficam_separadas(banco):
    banco.registrar_lote(corrida("run-001", inicio=1))
    banco.registrar_lote(corrida("run-002", inicio=10, amostras=5))
    resumos = banco.execucoes()
    assert [r.run_id for r in resumos] == ["run-002", "run-001"]
    assert [r.amostras for r in resumos] == [5, 3]


def test_mesmo_run_id_em_outro_boot_e_outra_execucao(banco):
    banco.registrar_lote(corrida(boot_id="boot-a"))
    banco.registrar_lote(corrida(boot_id="boot-b"))
    assert {r.boot_id for r in banco.execucoes()} == {"boot-a", "boot-b"}


def test_dados_fora_de_ordem(banco):
    frames = corrida(amostras=4)
    ordem = [frames[0], frames[-1], frames[3], frames[1], frames[4], frames[2]]
    assert set(banco.registrar_lote(ordem)) == {Resultado.GRAVADO}
    [resumo] = banco.execucoes()
    assert resumo.status == "concluida"
    assert resumo.duracao_ms == frames[-1].t_ms - frames[0].t_ms
    assert [a.seq for a in banco.amostras(resumo.id)] == [2, 3, 4, 5]


def test_execucao_sem_start_e_registrada(banco):
    banco.registrar_lote(corrida()[1:])
    [resumo] = banco.execucoes()
    assert not resumo.start_recebido
    assert resumo.status == "concluida"


def test_queda_do_app_marca_execucao_incompleta(tmp_path):
    caminho = tmp_path / "telemetria.db"
    frames = corrida(amostras=4)
    primeira = Armazenamento(caminho)
    primeira.abrir()
    primeira.registrar_lote(frames[:3])
    primeira.conexao.close()  # simula queda: sem fechar() o status fica em andamento no disco
    primeira._conexao = None

    with Armazenamento(caminho) as reaberta:
        [resumo] = reaberta.execucoes()
        assert resumo.status == "incompleta"
        assert resumo.app_interrompido

        # O robô continuou: a corrida volta a andamento e termina, sem perder a marca de lacuna.
        reaberta.registrar(frames[3])
        assert reaberta.execucoes()[0].status == "em_andamento"
        reaberta.registrar_lote(frames[4:])
        [resumo] = reaberta.execucoes()
        assert resumo.status == "concluida"
        assert resumo.app_interrompido


def test_fechar_com_corrida_aberta_marca_incompleta(tmp_path):
    caminho = tmp_path / "telemetria.db"
    with Armazenamento(caminho) as banco:
        banco.registrar_lote(corrida()[:2])
    with Armazenamento(caminho, somente_leitura=True) as leitura:
        assert leitura.execucoes()[0].status == "incompleta"


def test_somente_leitura_nao_altera_status(tmp_path):
    caminho = tmp_path / "telemetria.db"
    gravacao = Armazenamento(caminho)
    gravacao.abrir()
    gravacao.registrar_lote(corrida()[:2])
    with Armazenamento(caminho, somente_leitura=True) as leitura:
        assert leitura.execucoes()[0].status == "em_andamento"
        with pytest.raises(sqlite3.OperationalError):
            leitura.registrar(frame(20))
    gravacao.fechar()


def test_consulta_por_labirinto_estado_e_origem(banco):
    banco.registrar_lote(corrida("run-001", inicio=1))
    banco.registrar_lote([f.model_copy(update={"maze_id": "8x4"}) for f in corrida("run-002", inicio=10)])
    banco.registrar_lote(corrida("run-003", inicio=20)[:2])

    assert [r.run_id for r in banco.execucoes(maze_id="8x4")] == ["run-002"]
    assert [r.run_id for r in banco.execucoes(status="em_andamento")] == ["run-003"]
    assert len(banco.execucoes(origem="measured")) == 3  # conftest usa leituras medidas
    assert banco.execucoes(origem="simulated") == []
    assert banco.labirintos() == ["4x4", "8x4"]


def test_paginacao_e_limite(banco):
    for indice in range(5):
        banco.registrar_lote(corrida(f"run-{indice:03d}", inicio=indice * 10))
    pagina1 = banco.execucoes(limite=2)
    pagina2 = banco.execucoes(limite=2, deslocamento=2)
    assert len(pagina1) == len(pagina2) == 2
    assert not {r.id for r in pagina1} & {r.id for r in pagina2}
    with pytest.raises(ValueError):
        banco.execucoes(limite=101)
    with pytest.raises(ValueError):
        banco.execucoes(origem="chute")


def test_retencao_limita_amostras_por_execucao(tmp_path):
    with Armazenamento(tmp_path / "telemetria.db", max_amostras_por_execucao=2) as banco:
        banco.registrar_lote(corrida(amostras=5))
        [resumo] = banco.execucoes()
        assert resumo.amostras == 2
        assert resumo.amostras_descartadas == 3
        assert resumo.status == "concluida"


def test_podar_amostras_preserva_resumo_e_eventos(banco):
    banco.registrar_lote(corrida("run-001", inicio=1))
    banco.registrar_lote(corrida("run-002", inicio=10))
    assert banco.podar_amostras(manter_execucoes=1) == 3
    antiga = next(r for r in banco.execucoes() if r.run_id == "run-001")
    assert antiga.amostras == 0
    assert antiga.status == "concluida"
    assert len(banco.eventos(antiga.id)) == 2


def test_fora_de_corrida_guarda_so_falhas(banco):
    assert banco.registrar(frame(1, "sample", run_id=None)) == Resultado.IGNORADO
    assert banco.registrar(frame(2, "fault", run_id=None)) == Resultado.GRAVADO
    assert banco.execucoes() == []
    assert [e.fault.code for e in banco.eventos(None)] == ["SENSOR_TIMEOUT"]


def test_falhas_contadas_na_execucao(banco):
    frames = corrida()
    frames.insert(2, frame(50, "fault"))
    banco.registrar_lote(frames)
    assert banco.execucoes()[0].falhas == 1


def test_nao_trata_ausencia_como_zero(banco):
    banco.registrar_lote([frame(1, "start"), criar_frame(2, velocidade_esquerda=None)])
    [amostra] = banco.amostras(banco.execucoes()[0].id)
    assert amostra.velocidade_esquerda is None
    assert amostra.velocidade_direita == 98.0


def test_origens_de_um_frame():
    assert origens(criar_frame(1)) == {"measured", "estimated"}


def test_esquema_desconhecido_e_recusado(tmp_path):
    caminho = tmp_path / "telemetria.db"
    with sqlite3.connect(caminho) as conexao:
        conexao.execute("PRAGMA user_version = 99")
    conexao.close()
    with pytest.raises(RuntimeError, match="v99"):
        Armazenamento(caminho).abrir()


async def test_gravador_assincrono_grava_tudo_ao_fechar(tmp_path):
    caminho = tmp_path / "telemetria.db"
    gravador = GravadorAssincrono(Armazenamento(caminho), fila_max=4, lote_max=3)
    await gravador.iniciar()
    for f in gerar_frames(duracao_s=2.0):
        await gravador.gravar(f)
    await gravador.fechar()

    with Armazenamento(caminho, somente_leitura=True) as banco:
        [resumo] = banco.execucoes()
        assert resumo.status == "concluida"
        assert resumo.amostras + resumo.falhas == 20


async def test_gravador_exige_iniciar(tmp_path):
    gravador = GravadorAssincrono(Armazenamento(tmp_path / "x.db"))
    with pytest.raises(RuntimeError):
        await gravador.gravar(frame(1))
    await gravador.fechar()


async def test_erro_de_gravacao_nao_derruba_coleta(tmp_path):
    class Quebrado(Armazenamento):
        def registrar_lote(self, frames):
            raise sqlite3.OperationalError("disco cheio")

    gravador = GravadorAssincrono(Quebrado(tmp_path / "x.db"))
    await gravador.iniciar()
    await gravador.gravar(frame(1, "start"))
    await gravador.fechar()
    assert gravador.falhas_gravacao == 1
