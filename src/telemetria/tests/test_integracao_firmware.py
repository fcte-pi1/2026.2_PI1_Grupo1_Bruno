"""Integra publisher portátil, adaptador TCP e receptor/painel reais no host."""

import asyncio
import importlib
from contextlib import aclosing
from pathlib import Path

from telemetria.captura import CapturaJSONL, FonteArquivo
from telemetria.coleta import aplicar
from telemetria.estado import EstadoPainel
from telemetria.modelos import Frame
from telemetria.receptor import FonteTCPListen


class WlanLocal:
    def active(self, _ativa):
        pass

    def config(self, **_config):
        pass

    def isconnected(self):
        return True


async def test_firmware_tcp_ate_estado_e_captura_sem_trocar_corrida(monkeypatch, tmp_path):
    pasta = Path(__file__).resolve().parents[2] / "firmware"
    monkeypatch.syspath_prepend(str(pasta))
    core = importlib.import_module("telemetry")
    wifi = importlib.import_module("wifi_telemetry")
    captura = CapturaJSONL(tmp_path / "bancada.jsonl")
    fonte = FonteTCPListen("127.0.0.1", 0, captura=captura)
    estado = EstadoPainel()
    recebidos = []

    async def consumir():
        async with aclosing(fonte.eventos()) as eventos:
            async for evento in eventos:
                aplicar(evento, estado)
                if isinstance(evento, Frame):
                    recebidos.append(evento)
                    if evento.event == "finish":
                        return

    consumidor = asyncio.create_task(consumir())
    link = None
    try:
        async with asyncio.timeout(3):
            while fonte.porta_efetiva is None:
                await asyncio.sleep(0.001)
            link = wifi.WifiTelemetry(WlanLocal(), "fake-ap", "fake", "127.0.0.1", fonte.porta_efetiva)
            now = [0]
            publisher = core.TelemetryPublisher("robot-e2e", "boot-e2e", "run-e2e", "2x2", lambda: now[0])
            publisher.emit("start", "executando")
            for ciclo in range(100):
                now[0] = ciclo * 10
                publisher.record_control_cycle()
                publisher.sample("executando", battery_voltage=core.reading(8.1, "V", "simulated"))
                if ciclo == 40:
                    publisher.emit("fault", "executando", fault={"code": "SIM_SENSOR", "message": "simulado"})
                if ciclo == 60:
                    publisher.emit(
                        "map_update",
                        "executando",
                        map={
                            "width": 2,
                            "height": 2,
                            "source": "simulated",
                            "cells": [{"x": 0, "y": 0, "walls": 8, "known": 15}],
                        },
                    )
                link.service(publisher, now[0], byte_budget=97)
                await asyncio.sleep(0.001)
            now[0] = 1000
            publisher.emit("finish", "concluido")
            while publisher.pending_count:
                now[0] += 1
                link.service(publisher, now[0], byte_budget=97)
                await asyncio.sleep(0.001)
            await consumidor
        assert {frame.event for frame in recebidos} == {"start", "sample", "fault", "map_update", "finish"}
        assert {frame.run_id for frame in recebidos} == {"run-e2e"}
        assert [frame.seq for frame in recebidos] == sorted({frame.seq for frame in recebidos})
        assert estado.ultimo_frame.event == "finish"
        assert estado.descartados == 0
        assert fonte.estatisticas.invalidos == fonte.estatisticas.grandes == 0
        assert publisher.stats()["control_cycles"] == 100
        await captura.fechar()
        arquivo = FonteArquivo(captura.caminho, rapido=True)
        reproduzidos = [evento async for evento in arquivo.eventos() if isinstance(evento, Frame)]
        assert reproduzidos == recebidos
    finally:
        if link is not None:
            link.close()
        consumidor.cancel()
        await asyncio.gather(consumidor, return_exceptions=True)
        await captura.fechar()
