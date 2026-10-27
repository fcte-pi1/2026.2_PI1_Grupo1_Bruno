import pytest

from telemetria.mapa import CONFLITO, DESCONHECIDA, LIVRE, PAREDE, EstadoMapa, figura_mapa
from telemetria.modelos import FrameV2


def frame(seq, evento="sample", run_id="run-1", celulas=None, pose=None, rota=None, falha=None, **extra):
    dados = {
        "schema_version": 2,
        "robot_id": "micromouse-01",
        "boot_id": "boot-a",
        "run_id": run_id,
        "maze_id": "4x4",
        "seq": seq,
        "t_ms": seq * 100,
        "event": evento,
        "state": "executando",
    }
    if celulas is not None:
        dados["map"] = {"width": 4, "height": 4, "source": "estimated", "cells": celulas}
    if pose is not None or rota is not None:
        dados["navigation"] = {"width": 4, "height": 4}
        if pose is not None:
            x, y, heading = pose
            dados["navigation"]["pose"] = {"x": x, "y": y, "heading": heading, "source": "estimated"}
        if rota is not None:
            dados["navigation"]["route"] = {
                "source": "estimated",
                "cells": [{"x": x, "y": y} for x, y in rota],
            }
    if falha is not None:
        dados["fault"] = {"code": falha, "message": "teste"}
    return FrameV2.model_validate({**dados, **extra})


def aplicar(*frames):
    estado = EstadoMapa()
    for f in frames:
        estado.aplicar(f)
    return estado


def test_parede_livre_e_desconhecida_vem_dos_bits_known():
    # célula (0,0): norte livre, leste parede, sul e oeste parede; nada sobre (1,0)
    estado = aplicar(
        frame(1, "start"), frame(2, "map_update", celulas=[{"x": 0, "y": 0, "walls": 14, "known": 15}])
    )
    assert estado.estado_aresta(0, 0, "N") == LIVRE
    assert estado.estado_aresta(0, 0, "E") == PAREDE
    assert estado.estado_aresta(1, 0, "W") == PAREDE  # face compartilhada
    assert estado.estado_aresta(1, 0, "N") == DESCONHECIDA
    assert estado.estado_aresta(3, 3, "N") == DESCONHECIDA  # borda não observada não vira parede


def test_lado_sem_bit_known_continua_desconhecido():
    estado = aplicar(frame(1, "map_update", celulas=[{"x": 1, "y": 1, "walls": 1, "known": 1}]))
    assert estado.estado_aresta(1, 1, "N") == PAREDE
    assert estado.estado_aresta(1, 1, "E") == DESCONHECIDA


def test_leituras_que_discordam_aparecem_como_conflito():
    estado = aplicar(
        frame(1, "map_update", celulas=[{"x": 0, "y": 0, "walls": 2, "known": 2}]),
        frame(2, "map_update", celulas=[{"x": 1, "y": 0, "walls": 0, "known": 8}]),
    )
    assert estado.estado_aresta(0, 0, "E") == CONFLITO


def test_delta_substitui_a_celula_inteira():
    estado = aplicar(
        frame(1, "map_update", celulas=[{"x": 0, "y": 0, "walls": 2, "known": 2}]),
        frame(2, "map_update", celulas=[{"x": 0, "y": 0, "walls": 0, "known": 15}]),
    )
    assert estado.celulas[(0, 0)] == (0, 15)


def test_trajeto_segue_as_poses_sem_repetir_parado():
    estado = aplicar(
        frame(1, pose=(0, 0, "N")),
        frame(2, pose=(0, 0, "N")),
        frame(3, pose=(0, 1, "N")),
        frame(4, pose=(1, 1, "E")),
    )
    assert estado.trajeto == [(0, 0), (0, 1), (1, 1)]
    assert estado.pose.heading == "E"


def test_rota_planejada_separada_do_trajeto_e_rota_vazia_limpa():
    estado = aplicar(frame(1, pose=(0, 0, "N"), rota=[(0, 0), (0, 1), (1, 1)]))
    assert estado.rota == [(0, 0), (0, 1), (1, 1)]
    assert estado.trajeto == [(0, 0)]
    estado.aplicar(frame(2, rota=[]))
    assert estado.rota == []
    estado.aplicar(frame(3, pose=(0, 1, "N")))
    assert estado.rota == []  # navigation sem route não altera a rota


def test_nova_execucao_ou_boot_limpa_o_mapa():
    estado = aplicar(
        frame(1, "map_update", celulas=[{"x": 0, "y": 0, "walls": 1, "known": 1}], pose=(0, 0, "N"))
    )
    estado.aplicar(frame(2, "start", run_id="run-2"))
    assert estado.celulas == {} and estado.trajeto == [] and estado.pose is None
    estado.aplicar(
        frame(3, "map_update", celulas=[{"x": 2, "y": 2, "walls": 0, "known": 15}], boot_id="boot-b")
    )
    assert list(estado.celulas) == [(2, 2)]
    assert estado.chave[1] == "boot-b"


def test_falha_guarda_posicao_e_ignora_outra_execucao():
    estado = aplicar(frame(1, pose=(2, 1, "S")), frame(2, "fault", falha="ENCODER_STALL"))
    estado.aplicar(frame(3, "fault", run_id=None, falha="FORA"))
    assert [(f.codigo, f.posicao) for f in estado.falhas] == [("ENCODER_STALL", (2, 1))]


def test_frame_sem_mapa_nao_altera_estado():
    estado = aplicar(frame(1, pose=(0, 0, "N")))
    versao = estado.versao
    assert estado.aplicar(frame(2)) is False
    assert estado.versao == versao


def test_figura_nao_inventa_paredes():
    estado = aplicar(
        frame(1, "map_update", celulas=[{"x": 0, "y": 0, "walls": 12, "known": 15}], pose=(0, 0, "N"))
    )
    figura = figura_mapa(estado)
    tracos = {t["name"]: t for t in figura["data"]}
    paredes = [v for v in tracos["Parede"]["x"] if v is None]
    assert len(paredes) == 2  # só sul e oeste de (0,0)
    assert "Parede desconhecida" in tracos
    assert tracos["Robô (N, estimado)"]["x"] == [0.5]
    assert len(figura["layout"]["shapes"]) == 1


def test_figura_sem_dados():
    assert figura_mapa(EstadoMapa())["data"] == []


@pytest.mark.parametrize("lado", "NESW")
def test_todas_as_faces_tem_estado(lado):
    estado = aplicar(frame(1, "map_update", celulas=[{"x": 1, "y": 1, "walls": 15, "known": 15}]))
    assert estado.estado_aresta(1, 1, lado) == PAREDE
