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


def popular_com_mapa(caminho):
    with Armazenamento(caminho) as banco:
        banco.registrar_lote(list(gerar_frames(5, 10, 300, navegacao=True, maze_id="4x4")))
        return banco.execucoes()[0].id


async def test_replay_toca_e_pausa(user: User, tmp_path):
    caminho = tmp_path / "telemetria.db"
    execucao_id = popular_com_mapa(caminho)
    criar_pagina_historico(caminho)
    await user.open(f"/replay/{execucao_id}")
    await user.should_see("Replay da execução")
    tempo = next(r for r in user.find(ui.label).elements if r.text.startswith("00:00.0 /"))
    assert "mensagem 2 de" in tempo.text  # start e primeiro map_update chegam em t=0

    linha_tempo = user.find(ui.slider).elements.pop()
    inicio = linha_tempo.value
    user.find(marker=None, kind=ui.button).click()
    await asyncio.sleep(0.5)
    assert linha_tempo.value > inicio

    linha_tempo.set_value(linha_tempo.props["max"])
    await asyncio.sleep(0.3)
    grafico = user.find(ui.plotly).elements.pop()
    nomes = {traco["name"] for traco in grafico.figure["data"]}
    assert {"Parede", "Trajeto executado", "Parede desconhecida"} <= nomes


async def test_replay_de_execucao_inexistente(user: User, tmp_path):
    caminho = tmp_path / "telemetria.db"
    popular(caminho)
    criar_pagina_historico(caminho)
    await user.open("/replay/999")
    await user.should_see("Execução não encontrada.")


async def test_clicar_na_execucao_abre_o_replay(user: User, tmp_path):
    caminho = tmp_path / "telemetria.db"
    execucao_id = popular_com_mapa(caminho)
    criar_pagina_historico(caminho)
    await user.open("/historico")
    tabela = user.find(ui.table).elements.pop()
    user.find(ui.table).trigger("rowClick", [{}, tabela.rows[0], 0])
    await user.should_see("Replay da execução")
    assert tabela.rows[0]["id"] == execucao_id
