import json
from pathlib import Path

import pytest
from conftest import criar_frame
from pydantic import TypeAdapter, ValidationError

from telemetria.modelos import MAX_FRAME_BYTES, Ack, Comando, Frame

PROTOCOLO = Path(__file__).resolve().parents[3] / "docs" / "protocolo"
PACOTE = TypeAdapter(Frame | Comando | Ack)


def test_exemplos_compartilhados_validos():
    for linha in (PROTOCOLO / "validos.jsonl").read_bytes().splitlines():
        assert len(linha) <= MAX_FRAME_BYTES
        pacote = PACOTE.validate_json(linha)
        assert PACOTE.validate_json(pacote.model_dump_json()) == pacote


def test_exemplos_compartilhados_invalidos():
    for caso in json.loads((PROTOCOLO / "invalidos.json").read_text()):
        with pytest.raises(ValidationError):
            PACOTE.validate_json(json.dumps(caso["pacote"]))


def test_schema_versionado_corresponde_aos_modelos():
    schema = json.loads((PROTOCOLO / "v1.schema.json").read_text())
    del schema["$schema"]
    del schema["title"]
    assert schema == PACOTE.json_schema()


@pytest.mark.parametrize(
    "campo,valor", [("seq", True), ("seq", "1"), ("t_ms", 1.2), ("schema_version", True)]
)
def test_sem_coercao_de_identidade_e_tempo(campo, valor):
    dados = criar_frame(1).model_dump()
    dados[campo] = valor
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf"), "8.1", True])
def test_leituras_devem_ser_numeros_finitos(valor):
    dados = criar_frame(1).model_dump()
    dados["battery_voltage"]["value"] = valor
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


def test_nao_aceita_unidade_errada_no_campo():
    dados = criar_frame(1).model_dump()
    dados["battery_voltage"]["unit"] = "cm"
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


@pytest.mark.parametrize("evento", ["start", "finish"])
def test_ciclo_de_execucao_exige_run_id(evento):
    with pytest.raises(ValidationError):
        criar_frame(1, run_id=None, evento=evento)


@pytest.mark.parametrize(
    "alteracao",
    [
        {"cells": [{"x": 4, "y": 0, "walls": 1, "known": 15}]},
        {"cells": [{"x": 0, "y": 0, "walls": 1, "known": 0}]},
        {"cells": [{"x": 0, "y": 0, "walls": 0, "known": 15}] * 2},
        {"cells": []},
    ],
)
def test_mapa_rejeita_coordenadas_e_mascaras_invalidas(alteracao):
    dados = criar_frame(1).model_dump()
    dados.update(event="map_update", map={"width": 4, "height": 4, "source": "estimated", **alteracao})
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)
