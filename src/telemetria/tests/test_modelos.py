import pytest
from conftest import criar_frame
from pydantic import ValidationError

from telemetria.modelos import Frame


def test_ida_e_volta_em_json():
    frame = criar_frame(3)
    assert Frame.model_validate_json(frame.model_dump_json()) == frame


def test_rejeita_versao_incompativel():
    dados = criar_frame(1).model_dump()
    dados["schema_version"] = 2
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


def test_rejeita_campo_desconhecido():
    dados = criar_frame(1).model_dump()
    dados["extra"] = True
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


def test_rejeita_sequencia_negativa():
    dados = criar_frame(1).model_dump()
    dados["seq"] = -1
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


def test_rejeita_origem_desconhecida():
    dados = criar_frame(1).model_dump()
    dados["battery_voltage"]["source"] = "chute"
    with pytest.raises(ValidationError):
        Frame.model_validate(dados)


def test_campos_opcionais_podem_faltar():
    frame = Frame(
        schema_version=1,
        robot_id="micromouse-01",
        boot_id="boot-a",
        seq=0,
        t_ms=0,
        event="start",
        state="pronto",
    )
    assert frame.wheel_left is None
    assert frame.sensors == {}
