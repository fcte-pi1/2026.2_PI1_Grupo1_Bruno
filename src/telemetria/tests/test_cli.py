import json
import subprocess
import sys

import pytest

from telemetria.__main__ import argumentos, criar_fonte, headless
from telemetria.captura import FonteArquivo
from telemetria.fonte_simulada import FonteSimulada
from telemetria.gerador import gerar_frames
from telemetria.receptor import FonteSerial, FonteTCPListen


def test_default_simulador_e_10hz():
    args = argumentos([])
    assert args.taxa == 10 and args.baud == 115200
    assert isinstance(criar_fonte(args), FonteSimulada)


@pytest.mark.parametrize(
    "opcoes,tipo",
    [
        (["--serial", "COM3"], FonteSerial),
        (["--tcp-listen", "127.0.0.1:8765"], FonteTCPListen),
        (["--arquivo", "fake.jsonl"], FonteArquivo),
    ],
)
def test_selecao_fonte(opcoes, tipo):
    assert isinstance(criar_fonte(argumentos(opcoes)), tipo)


@pytest.mark.parametrize(
    "opcoes",
    [
        ["--serial", "COM3", "--tcp-listen", "localhost:1234"],
        ["--tcp-listen", "localhost"],
        ["--taxa", "0"],
        ["--taxa", "nan"],
        ["--baud", "0"],
        ["--captura", "x"],
        ["--limite", "1"],
    ],
)
def test_argumentos_invalidos_falham(opcoes):
    with pytest.raises(SystemExit):
        argumentos(opcoes)


async def test_headless_limite_sem_ui(capsys):
    await headless(FonteSimulada(), limite=1)
    assert json.loads(capsys.readouterr().out)["event"] == "start"


def test_playback_headless_subprocess_nao_importa_ui(tmp_path):
    caminho = tmp_path / "fake.jsonl"
    frames = list(gerar_frames(duracao_s=0.1))
    caminho.write_text("\n".join(f.model_dump_json() for f in frames) + "\n")
    resultado = subprocess.run(
        [sys.executable, "-m", "telemetria", "--arquivo", str(caminho), "--headless", "--rapido"],
        check=True,
        capture_output=True,
    )
    assert [json.loads(linha) for linha in resultado.stdout.splitlines()] == [f.model_dump() for f in frames]
    assert b"fim do arquivo" in resultado.stderr


async def test_headless_filtra_duplicados_ordem_boots_e_execucoes(capsys):
    from telemetria.fonte_simulada import SimuladorRobo
    from telemetria.modelos import LinkAberto, LinkFechado

    base = SimuladorRobo().iniciar(0)
    a1 = base.model_copy(update={"boot_id": "boot-a", "run_id": "run-a"})
    a2 = a1.model_copy(update={"seq": 2, "t_ms": 100, "event": "sample"})
    a3 = a1.model_copy(update={"seq": 3, "t_ms": 200, "run_id": "run-b"})
    atrasado = a1.model_copy(update={"seq": 4, "t_ms": 300, "event": "sample"})
    b1 = a1.model_copy(update={"boot_id": "boot-b"})
    b2 = b1.model_copy(update={"seq": 2, "t_ms": 100, "event": "sample"})

    class Lista:
        async def eventos(self):
            for evento in [
                LinkAberto("teste"),
                a1,
                a1,
                a2,
                a3,
                atrasado,
                LinkFechado("queda"),
                LinkAberto("reconectado"),
                b1,
                a2,
                b2,
            ]:
                yield evento

    await headless(Lista(), limite=5)
    assert [json.loads(linha) for linha in capsys.readouterr().out.splitlines()] == [
        f.model_dump() for f in [a1, a2, a3, b1, b2]
    ]
