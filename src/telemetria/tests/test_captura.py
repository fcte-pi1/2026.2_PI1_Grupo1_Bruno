import asyncio
from contextlib import aclosing

import pytest

from telemetria.captura import CapturaBruta, FonteArquivo
from telemetria.gerador import gerar_frames
from telemetria.modelos import Frame, LinkFechado


async def test_captura_reproduz_frames_fragmentos_invalidos_e_fronteira(tmp_path):
    caminho = tmp_path / "captura.jsonl"
    captura = CapturaBruta(caminho)
    frames = list(gerar_frames(duracao_s=0.1))
    dados = (frames[0].model_dump_json() + "\n").encode()
    await captura.gravar(b"\xff\n" + dados[:17])
    await captura.gravar(dados[17:] + dados[:17])
    await captura.fim_segmento()
    await captura.gravar((frames[-1].model_dump_json() + "\n").encode())
    await captura.fechar()
    fonte = FonteArquivo(caminho, rapido=True)
    eventos = [evento async for evento in fonte.eventos()]
    assert [f for f in eventos if isinstance(f, Frame)] == [frames[0], frames[-1]]
    assert fonte.estatisticas.invalidos == 1
    assert fonte.estatisticas.incompletos == 1
    assert len([e for e in eventos if isinstance(e, LinkFechado)]) == 2


async def test_captura_limita_disco_sem_truncar_registros(tmp_path):
    caminho = tmp_path / "captura.jsonl"
    captura = CapturaBruta(caminho, max_bytes=200)
    await captura.gravar(b"abc\n")
    tamanho = caminho.stat().st_size
    await captura.gravar(b"x" * 100_000)
    await captura.fechar()
    assert captura.saturada
    assert caminho.stat().st_size == tamanho <= 200
    assert caminho.read_bytes().endswith(b"\n")


async def test_captura_nao_sobrescreve_arquivo(tmp_path):
    caminho = tmp_path / "existente"
    caminho.write_bytes(b"original")
    captura = CapturaBruta(caminho)
    await captura.gravar(b"abc")
    assert captura.saturada
    assert caminho.read_bytes() == b"original"


async def test_playback_jsonl_puro_limita_linhas_e_cede_ao_loop(tmp_path):
    caminho = tmp_path / "frames.jsonl"
    frames = list(gerar_frames(taxa_hz=100, duracao_s=1))
    caminho.write_bytes(
        b"x" * 30_000 + b"\n" + b"".join((f.model_dump_json() + "\n").encode() for f in frames)
    )
    fonte = FonteArquivo(caminho, rapido=True)
    eventos = [evento async for evento in fonte.eventos()]
    assert [f for f in eventos if isinstance(f, Frame)] == frames
    assert fonte.estatisticas.grandes == 1


async def test_playback_lento_cancelavel(tmp_path):
    caminho = tmp_path / "frames.jsonl"
    frames = list(gerar_frames(duracao_s=0.1))
    caminho.write_text("\n".join(f.model_dump_json() for f in frames) + "\n")
    fonte = FonteArquivo(caminho, taxa_hz=0.1)
    async with aclosing(fonte.eventos()) as eventos:
        await anext(eventos)
        assert isinstance(await anext(eventos), Frame)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(anext(eventos), timeout=0.02)


async def test_arquivo_fecha_ao_cancelar_apos_link_aberto(tmp_path, monkeypatch):
    from pathlib import Path

    caminho = tmp_path / "fake.jsonl"
    caminho.write_bytes(b"")
    arquivo = caminho.open("rb")
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: arquivo)
    eventos = FonteArquivo(caminho).eventos()
    await anext(eventos)
    await eventos.aclose()
    assert arquivo.closed


async def test_disco_cheio_suspende_captura(tmp_path):
    class DiscoCheio:
        def write(self, dados):
            raise OSError("disco cheio")

        def close(self):
            self.fechado = True

    captura = CapturaBruta(tmp_path / "captura")
    arquivo = DiscoCheio()
    captura._arquivo = arquivo
    await captura.gravar(b"dados\n")
    assert captura.saturada and arquivo.fechado
    await captura.gravar(b"proximos\n")


async def test_abertura_cancelada_recolhe_e_fecha_recurso(tmp_path, monkeypatch):
    import time
    from pathlib import Path

    from telemetria.captura import _abrir_arquivo

    caminho = tmp_path / "fake"
    caminho.write_bytes(b"")
    arquivo = caminho.open("rb")

    def abrir_lento(*args, **kwargs):
        time.sleep(0.03)
        return arquivo

    monkeypatch.setattr(Path, "open", abrir_lento)
    tarefa = asyncio.create_task(_abrir_arquivo(caminho, "rb"))
    await asyncio.sleep(0.01)
    tarefa.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert arquivo.closed
