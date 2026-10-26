import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from telemetria.modelos import FRAMES_TELEMETRIA, MAX_FRAME_BYTES, Frame, FrameV2
from telemetria.receptor import DecodificadorJSONL

PROTOCOLO = Path(__file__).resolve().parents[3] / "docs" / "protocolo"
VALIDOS = [json.loads(linha) for linha in (PROTOCOLO / "v2.validos.jsonl").read_text().splitlines()]
INVALIDOS = json.loads((PROTOCOLO / "v2.invalidos.json").read_text())


@pytest.fixture
def firmware(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "firmware"))
    return importlib.import_module("telemetry")


def publicar(core, pacote):
    publisher = core.TelemetryPublisher(
        pacote["robot_id"],
        pacote["boot_id"],
        pacote["run_id"],
        pacote["maze_id"],
        lambda: pacote["t_ms"],
        schema_version=pacote["schema_version"],
        include_stats=False,
    )
    envelope = {"schema_version", "robot_id", "boot_id", "run_id", "maze_id", "seq", "t_ms", "event", "state"}
    payload = {chave: valor for chave, valor in pacote.items() if chave not in envelope}
    assert publisher.emit(pacote["event"], pacote["state"], **payload)
    dados = bytearray()

    def escrever(parte):
        dados.extend(parte)
        return len(parte)

    writer = core.BoundedWriter(escrever)
    while publisher.pending_count:
        publisher.service(writer, byte_budget=31)
    return bytes(dados)


@pytest.mark.parametrize("pacote", VALIDOS, ids=lambda pacote: str(pacote["seq"]))
def test_v2_valido_nas_duas_pontas_e_fragmentado(firmware, pacote):
    esperado = FrameV2.model_validate(pacote)
    dados = publicar(firmware, pacote)
    assert len(dados) - 1 <= MAX_FRAME_BYTES
    decodificador = DecodificadorJSONL()
    recebidos = []
    for byte in dados:
        recebidos.extend(decodificador.feed(bytes([byte])))
    assert recebidos == [esperado.model_copy(update={"seq": 0})]
    assert isinstance(recebidos[0], FrameV2)
    assert decodificador.estatisticas.invalidos == 0
    with pytest.raises(ValidationError):
        Frame.model_validate(pacote)


@pytest.mark.parametrize("caso", INVALIDOS, ids=lambda caso: caso["nome"])
def test_v2_invalido_nas_duas_pontas(firmware, caso):
    pacote = caso["pacote"]
    with pytest.raises(ValidationError):
        FRAMES_TELEMETRIA.validate_json(json.dumps(pacote))
    with pytest.raises(ValueError):
        publicar(firmware, pacote)
    decodificador = DecodificadorJSONL()
    dados = json.dumps(pacote, separators=(",", ":")).encode() + b"\n"
    proximo = json.dumps(VALIDOS[0]).encode() + b"\n"
    assert len(decodificador.feed(dados + proximo)) == 1
    assert decodificador.estatisticas.invalidos + decodificador.estatisticas.grandes == 1


def test_schema_v2_corresponde_ao_modelo():
    schema = json.loads((PROTOCOLO / "v2.schema.json").read_text())
    esperado = TypeAdapter(FrameV2).json_schema()
    esperado["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    esperado["title"] = "Micromouse — contrato v2"
    assert schema == esperado


def test_rota_grande_respeita_limite_sem_truncar(firmware):
    pacote = deepcopy(VALIDOS[1])
    pacote["navigation"]["route"]["cells"] = [{"x": i % 2, "y": 0} for i in range(1024)]
    FrameV2.model_validate(pacote)
    publisher = firmware.TelemetryPublisher("r", "b", "run", "maze", lambda: 0, schema_version=2)
    assert not publisher.emit("sample", "executando", navigation=pacote["navigation"])
    assert publisher.pending_count == 0
    assert publisher.stats()["samples_dropped"] == 1
    pacote["navigation"]["route"]["cells"].append({"x": 0, "y": 0})
    with pytest.raises(ValidationError):
        FrameV2.model_validate(pacote)
    with pytest.raises(ValueError):
        publisher.emit("sample", "executando", navigation=pacote["navigation"])


def test_v1_continua_rejeitando_navegacao_mesmo_nula(firmware):
    pacote = {**VALIDOS[0], "schema_version": 1, "navigation": None}
    with pytest.raises(ValidationError):
        FRAMES_TELEMETRIA.validate_python(pacote)
    with pytest.raises(ValueError):
        publicar(firmware, pacote)
