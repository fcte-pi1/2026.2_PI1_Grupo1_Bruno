import random

import pytest

from telemetria.armazenamento import Armazenamento
from telemetria.estado import EstadoPainel
from telemetria.fonte_simulada import NavegacaoSimulada, SimuladorRobo, gerar_labirinto
from telemetria.gerador import gerar_frames
from telemetria.mapa import EstadoMapa
from telemetria.modelos import FRAMES_TELEMETRIA, MAX_FRAME_BYTES, FrameV2
from telemetria.replay import Replay


def captura(seed=7, maze_id="4x4"):
    return list(gerar_frames(seed, taxa_hz=10, duracao_s=300, navegacao=True, maze_id=maze_id))


@pytest.mark.parametrize("maze_id", ["4x4", "8x4", "12x4"])
def test_simulador_chega_ao_objetivo_e_respeita_o_contrato(maze_id):
    frames = captura(maze_id=maze_id)
    largura, altura = (int(v) for v in maze_id.split("x"))
    assert frames[0].event == "start" and frames[-1].event == "finish"
    for f in frames:
        assert isinstance(f, FrameV2)
        assert len(f.model_dump_json().encode()) <= MAX_FRAME_BYTES
        FRAMES_TELEMETRIA.validate_json(f.model_dump_json())
    estado = EstadoMapa()
    for f in frames:
        estado.aplicar(f)
    assert (estado.pose.x, estado.pose.y) == (largura - 1, altura - 1)


def test_simulador_so_revela_celulas_visitadas():
    frames = captura(seed=3, maze_id="8x4")
    reveladas = {(c.x, c.y) for f in frames if f.map is not None for c in f.map.cells}
    visitadas = {
        (f.navigation.pose.x, f.navigation.pose.y) for f in frames if f.navigation and f.navigation.pose
    }
    assert reveladas == visitadas
    assert len(reveladas) < 32


def test_simulador_sem_mapa_continua_v1_e_igual():
    antes = [f.model_dump_json() for f in gerar_frames(7, 10, 2)]
    depois = [f.model_dump_json() for f in gerar_frames(7, 10, 2, navegacao=False)]
    assert antes == depois
    assert all('"schema_version":1' in linha for linha in antes)


def test_labirinto_gerado_tem_caminho_ate_o_objetivo():
    paredes = gerar_labirinto(12, 4, random.Random(1))
    assert all(0 <= v <= 15 for v in paredes.values())
    nav = NavegacaoSimulada(12, 4, random.Random(1))
    nav.conhecidas = dict(nav._paredes_reais)
    assert nav.planejar()[-1] == (11, 3)


def test_labirinto_invalido_e_recusado():
    with pytest.raises(ValueError):
        SimuladorRobo(navegacao=True, maze_id="quatro")


def test_replay_reconstroi_igual_a_aplicacao_sequencial():
    frames = captura(seed=11, maze_id="8x4")
    replay = Replay(frames, intervalo_copia=7)
    for aplicados in (0, 1, 6, 7, 8, 50, len(frames) - 1, len(frames)):
        esperado = EstadoMapa()
        for f in frames[:aplicados]:
            esperado.aplicar(f)
        assert replay.estado(aplicados).resumo() == esperado.resumo()


def test_replay_busca_por_tempo():
    frames = captura()
    replay = Replay(frames)
    assert replay.aplicados_ate(replay.inicio_ms - 1) == 0
    assert replay.aplicados_ate(replay.fim_ms) == replay.total
    meio = frames[len(frames) // 2].t_ms
    assert replay.frames[replay.aplicados_ate(meio) - 1].t_ms == meio


def test_replay_vazio():
    replay = Replay([])
    assert replay.total == 0 and replay.estado(0).largura is None


def test_tela_ao_vivo_e_replay_da_mesma_captura_coincidem(tmp_path):
    frames = captura(seed=5, maze_id="12x4")
    ao_vivo = EstadoPainel()
    for f in frames:
        ao_vivo.registrar(f)

    with Armazenamento(tmp_path / "t.db") as banco:
        banco.registrar_lote(frames)
        [resumo] = banco.execucoes()
        salvos = banco.frames(resumo.id)

    assert [f.seq for f in salvos] == [f.seq for f in frames]
    assert Replay(salvos).final.resumo() == ao_vivo.mapa.resumo()
