import asyncio
import subprocess
import sys

import pytest
from nicegui import ui
from nicegui.testing import User

from telemetria.armazenamento import Armazenamento
from telemetria.gerador import gerar_frames
from telemetria.historico import main
from telemetria.pagina_historico import criar_pagina_historico


def popular(caminho, labirintos=("4x4", "8x4")):
    with Armazenamento(caminho) as banco:
        for indice, maze_id in enumerate(labirintos):
            frames = gerar_frames(seed=indice, duracao_s=0.5)
            banco.registrar_lote([f.model_copy(update={"maze_id": maze_id}) for f in frames])


def test_cli_lista_e_filtra_por_labirinto(tmp_path, capsys):
    caminho = tmp_path / "telemetria.db"
    popular(caminho)
    main(["--banco", str(caminho)])
    saida = capsys.readouterr().out
    assert "4x4" in saida and "8x4" in saida
    assert "concluída (concluido)" in saida
    assert "simulado" in saida

    main(["--banco", str(caminho), "--labirinto", "8x4"])
    linhas = capsys.readouterr().out.splitlines()
    assert len(linhas) == 2 and "8x4" in linhas[1]


def test_cli_sem_resultado_e_banco_inexistente(tmp_path, capsys):
    caminho = tmp_path / "telemetria.db"
    popular(caminho)
    main(["--banco", str(caminho), "--estado", "incompleta"])
    assert "Nenhuma execução encontrada." in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["--banco", str(tmp_path / "nao-existe.db")])
    with pytest.raises(SystemExit):
        main(["--banco", str(caminho), "--limite", "0"])


def test_playback_headless_salva_no_banco(tmp_path):
    jsonl = tmp_path / "fake.jsonl"
    banco = tmp_path / "telemetria.db"
    frames = list(gerar_frames(duracao_s=0.5))
    jsonl.write_text("\n".join(f.model_dump_json() for f in frames) + "\n")
    comando = [sys.executable, "-m", "telemetria", "--arquivo", str(jsonl), "--headless", "--rapido"]
    subprocess.run([*comando, "--banco", str(banco)], check=True, capture_output=True)
    # Reproduzir a mesma captura de novo não duplica a execução.
    subprocess.run([*comando, "--banco", str(banco)], check=True, capture_output=True)

    with Armazenamento(banco, somente_leitura=True) as leitura:
        [resumo] = leitura.execucoes()
        assert resumo.status == "concluida"
        assert resumo.amostras + resumo.falhas == len(frames) - 2


async def test_pagina_historico_mostra_e_filtra(user: User, tmp_path):
    caminho = tmp_path / "telemetria.db"
    popular(caminho)
    criar_pagina_historico(caminho)
    await user.open("/historico")
    await user.should_see("Histórico de execuções")
    tabela = user.find(ui.table).elements.pop()
    assert sorted(linha["2"] for linha in tabela.rows) == ["4x4", "8x4"]

    labirinto = next(s for s in user.find(ui.select).elements if s.props.get("label") == "Labirinto")
    labirinto.value = "8x4"
    await asyncio.sleep(0.3)
    assert [linha["2"] for linha in tabela.rows] == ["8x4"]


async def test_pagina_historico_sem_banco(user: User, tmp_path):
    criar_pagina_historico(tmp_path / "ainda-nao-existe.db")
    await user.open("/historico")
    await user.should_see("Nenhuma execução encontrada.")
