import asyncio
import os
from contextlib import aclosing

import pytest
import serial

from telemetria.fonte_simulada import SimuladorRobo
from telemetria.modelos import Frame, LinkAberto, LinkFechado
from telemetria.receptor import (
    MAX_PAYLOAD,
    DecodificadorJSONL,
    EstatisticasRecepcao,
    FonteSerial,
    FonteTCPListen,
    _FilaEventos,
)


def linha(seq: int = 1, evento: str = "sample") -> bytes:
    frame = SimuladorRobo().iniciar(0.0)
    return (frame.model_copy(update={"seq": seq, "event": evento}).model_dump_json() + "\n").encode()


def test_fragmentacao_utf8_json_e_multiplas_linhas():
    dados = linha(1) + linha(2)
    decodificador = DecodificadorJSONL()
    frames = []
    for byte in dados:
        frames.extend(decodificador.feed(bytes([byte])))
    assert [f.seq for f in frames] == [1, 2]
    assert decodificador.estatisticas.frames == 2


def test_limite_exclui_lf_e_resincroniza_sem_acumular_payload():
    decodificador = DecodificadorJSONL()
    payload = linha().rstrip(b"\n")
    assert len(payload) < MAX_PAYLOAD
    assert len(decodificador.feed(payload + b" " * (MAX_PAYLOAD - len(payload)) + b"\n")) == 1
    assert decodificador.feed(b"x" * (MAX_PAYLOAD + 1)) == []
    assert len(decodificador._buffer) == 0
    assert decodificador.feed(b"x" * 100_000) == []
    assert [f.seq for f in decodificador.feed(b"\n" + linha(3))] == [3]
    assert decodificador.estatisticas.grandes == 1


@pytest.mark.parametrize("invalida", [b"\xff\n", b"{\n", b"{}\n", b'{"ack":"ok"}\n', b"\n"])
def test_rejeita_invalida_e_aceita_proxima(invalida):
    decodificador = DecodificadorJSONL()
    assert len(decodificador.feed(invalida + linha())) == 1
    assert decodificador.estatisticas.invalidos == 1


@pytest.mark.parametrize(
    ("antes", "depois"),
    [
        (b'"schema_version":1', b'"schema_version":2'),
        (b'"seq":1', b'"seq":"1"'),
        (b'"t_ms":0', b'"t_ms":NaN'),
        (b'"t_ms":0', b'"t_ms":-1'),
    ],
)
def test_rejeita_versao_tipos_e_nao_finitos(antes, depois):
    decodificador = DecodificadorJSONL()
    assert decodificador.feed(linha().replace(antes, depois)) == []
    assert decodificador.estatisticas.invalidos == 1


def test_final_de_link_descarta_fragmento_sem_fundir_boots():
    decodificador = DecodificadorJSONL()
    assert decodificador.feed(linha()[:30]) == []
    decodificador.finalizar()
    assert len(decodificador.feed(linha(2))) == 1
    assert decodificador.estatisticas.incompletos == 1


async def test_sobrecarga_preserva_criticos_e_amostra_mais_recente():
    stats = EstatisticasRecepcao()
    fila = _FilaEventos(3, stats)
    frames = DecodificadorJSONL().feed(linha(1, "start") + linha(2) + linha(3) + linha(4, "finish"))
    for frame in frames:
        await fila.colocar(frame)
    assert [(await fila.retirar()).seq for _ in range(3)] == [1, 3, 4]
    assert stats.amostras_descartadas == 1


async def test_fila_so_criticos_aplica_backpressure_e_descarta_sample():
    stats = EstatisticasRecepcao()
    fila = _FilaEventos(1, stats)
    await fila.colocar(LinkAberto("teste"))
    await fila.colocar(DecodificadorJSONL().feed(linha())[0])
    tarefa = asyncio.create_task(fila.colocar(LinkFechado("fim")))
    await asyncio.sleep(0)
    assert not tarefa.done()
    assert isinstance(await fila.retirar(), LinkAberto)
    await asyncio.wait_for(tarefa, 1)
    assert isinstance(await fila.retirar(), LinkFechado)
    assert stats.amostras_descartadas == 1


@pytest.mark.skipif(os.name != "posix", reason="PTY é integração Linux; pySerial loop:// é multiplataforma")
async def test_serial_real_pty_fragmentado_reconexao_e_cancelamento():
    import pty

    mestre, escravo = pty.openpty()
    fonte = FonteSerial(os.ttyname(escravo), timeout_s=0.02, reconexao_s=0.01)
    try:
        async with aclosing(fonte.eventos()) as eventos:
            assert isinstance(await asyncio.wait_for(anext(eventos), 2), LinkAberto)
            os.write(mestre, linha()[:20])
            os.write(mestre, linha()[20:])
            frame = await asyncio.wait_for(anext(eventos), 2)
            assert isinstance(frame, Frame) and frame.seq == 1
            os.close(mestre)
            mestre = -1
            assert isinstance(await asyncio.wait_for(anext(eventos), 2), LinkFechado)
    finally:
        if mestre >= 0:
            os.close(mestre)
        os.close(escravo)
    assert not fonte._rodando


async def test_pyserial_loop_url_recebe_sem_bloquear_loop(monkeypatch):
    porta = serial.serial_for_url("loop://", timeout=0.02)
    original = serial.serial_for_url
    monkeypatch.setattr(serial, "serial_for_url", lambda *args, **kwargs: porta)
    fonte = FonteSerial("loop://", timeout_s=0.02)
    async with aclosing(fonte.eventos()) as eventos:
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), LinkAberto)
        porta.write(linha())
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), Frame)
    assert not porta.is_open
    monkeypatch.setattr(serial, "serial_for_url", original)


async def esperar_porta(fonte):
    async with asyncio.timeout(2):
        while fonte.porta_efetiva is None:
            await asyncio.sleep(0.005)
    return fonte.porta_efetiva


async def test_tcp_localhost_fragmentacao_reconexao_sem_inventar_start():
    fonte = FonteTCPListen("127.0.0.1", 0, timeout_s=0.02)
    async with aclosing(fonte.eventos()) as eventos:
        primeiro = asyncio.create_task(anext(eventos))
        porta = await esperar_porta(fonte)
        _, escritor = await asyncio.open_connection("127.0.0.1", porta)
        assert isinstance(await asyncio.wait_for(primeiro, 2), LinkAberto)
        escritor.write(linha(4)[:30])
        await escritor.drain()
        await asyncio.sleep(0.03)
        escritor.write(linha(4)[30:])
        await escritor.drain()
        frame = await asyncio.wait_for(anext(eventos), 2)
        assert frame.seq == 4 and frame.event == "sample"
        escritor.close()
        await escritor.wait_closed()
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), LinkFechado)
        leitor2, escritor2 = await asyncio.open_connection("127.0.0.1", porta)
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), LinkAberto)
        escritor2.write(linha(5))
        await escritor2.drain()
        frame2 = await asyncio.wait_for(anext(eventos), 2)
        assert frame2.run_id == frame.run_id and frame2.seq == 5
        # Fechar a fonte deve fechar socket, inclusive com cliente silencioso.
    assert await asyncio.wait_for(leitor2.read(), 2) == b""
    escritor2.close()
    await escritor2.wait_closed()
    assert fonte.porta_efetiva is None and not fonte._clientes


@pytest.mark.parametrize("dados", [b'{"a":1,"a":2}\n', b"[" * 1800 + b"]" * 1800 + b"\n"])
def test_json_ambiguo_ou_profundidade_excessiva_nao_derruba_parser(dados):
    decodificador = DecodificadorJSONL()
    assert len(decodificador.feed(dados + linha())) == 1
    assert decodificador.estatisticas.invalidos == 1


async def test_tcp_captura_indisponivel_continua_recebendo_e_fecha_em_sobrecarga(tmp_path):
    from telemetria.captura import CapturaBruta

    caminho = tmp_path / "existente"
    caminho.write_bytes(b"original")
    captura = CapturaBruta(caminho)
    fonte = FonteTCPListen("127.0.0.1", 0, fila_max=1, captura=captura)
    async with aclosing(fonte.eventos()) as eventos:
        primeiro = asyncio.create_task(anext(eventos))
        porta = await esperar_porta(fonte)
        _, escritor = await asyncio.open_connection("127.0.0.1", porta)
        await asyncio.wait_for(primeiro, 2)
        escritor.write(linha(1, "start"))
        await escritor.drain()
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), Frame)
        assert captura.saturada
        # Crítico enche fila e o EOF coloca outro crítico em backpressure.
        escritor.write(linha(2, "finish"))
        await escritor.drain()
        escritor.close()
        await escritor.wait_closed()
        await asyncio.sleep(0.03)
    assert not fonte._clientes
    assert caminho.read_bytes() == b"original"
    await captura.fechar()


async def test_serial_captura_indisponivel_continua_recebendo_e_fecha_porta(tmp_path, monkeypatch):
    from telemetria.captura import CapturaBruta

    caminho = tmp_path / "existente"
    caminho.write_bytes(b"original")
    captura = CapturaBruta(caminho)
    porta = serial.serial_for_url("loop://", timeout=0.02)
    monkeypatch.setattr(serial, "serial_for_url", lambda *args, **kwargs: porta)
    fonte = FonteSerial("loop://", timeout_s=0.02, captura=captura)
    async with aclosing(fonte.eventos()) as eventos:
        await asyncio.wait_for(anext(eventos), 2)
        porta.write(linha())
        assert isinstance(await asyncio.wait_for(anext(eventos), 2), Frame)
        assert captura.saturada
    assert not porta.is_open
    assert caminho.read_bytes() == b"original"
    await captura.fechar()
