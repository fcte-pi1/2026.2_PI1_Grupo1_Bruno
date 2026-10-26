import json
import subprocess
import sys

import pytest

from telemetria.gerador import gerar_frames
from telemetria.modelos import Frame


def test_mesma_seed_mesmos_bytes_e_tempos_nao_dependem_de_wall_clock():
    a = [f.model_dump_json() for f in gerar_frames(seed=123, taxa_hz=10, duracao_s=1)]
    b = [f.model_dump_json() for f in gerar_frames(seed=123, taxa_hz=10, duracao_s=1)]
    assert a == b
    frames = [Frame.model_validate_json(linha) for linha in a]
    assert [f.t_ms for f in frames] == [0, *range(100, 1100, 100), 1000]
    assert frames[0].event == "start" and frames[-1].event == "finish"
    assert all(f.battery_voltage.source == "simulated" for f in frames)


@pytest.mark.parametrize("taxa,duracao", [(0, 1), (-1, 1), (1, 0), (float("inf"), 1)])
def test_rejeita_taxa_ou_duracao_invalida(taxa, duracao):
    with pytest.raises(ValueError):
        list(gerar_frames(taxa_hz=taxa, duracao_s=duracao))


def test_cli_stdout_e_arquivo_identicos(tmp_path):
    comando = [sys.executable, "-m", "telemetria.gerador", "--rapido", "--duracao", "0.1"]
    stdout = subprocess.run(comando, check=True, capture_output=True).stdout
    caminho = tmp_path / "fake.jsonl"
    subprocess.run([*comando, "--output", str(caminho)], check=True, capture_output=True)
    assert stdout == caminho.read_bytes()
    assert all(json.loads(linha)["schema_version"] == 1 for linha in stdout.splitlines())
