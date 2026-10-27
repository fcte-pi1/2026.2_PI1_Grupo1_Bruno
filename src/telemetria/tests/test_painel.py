import asyncio

from conftest import criar_frame
from nicegui import ui
from nicegui.testing import User

from telemetria.estado import EstadoPainel
from telemetria.formatacao import INDISPONIVEL, SEM_LEITURA
from telemetria.modelos import Falha
from telemetria.painel import criar_pagina


async def esperar_renderizacao() -> None:
    await asyncio.sleep(0.4)


async def test_mostra_aguardando_e_selo_de_fonte_simulada(user: User):
    criar_pagina(EstadoPainel(), fonte_simulada=True, intervalo_s=0.1)
    await user.open("/")
    await user.should_see("aguardando")
    await user.should_see("FONTE SIMULADA")
    await user.should_see("Percentual de carga não estimado")


async def test_sem_selo_quando_fonte_nao_e_simulada(user: User):
    criar_pagina(EstadoPainel(), fonte_simulada=False, intervalo_s=0.1)
    await user.open("/")
    await user.should_not_see("FONTE SIMULADA")


async def test_exibe_valores_origem_e_lacunas(user: User):
    estado = EstadoPainel()
    criar_pagina(estado, fonte_simulada=False, intervalo_s=0.1)
    await user.open("/")
    estado.link_aberto("teste")
    estado.registrar(criar_frame(7, velocidade_esquerda=None))
    await esperar_renderizacao()
    await user.should_see("conectado")
    await user.should_see("run-001")
    await user.should_see(SEM_LEITURA)
    await user.should_see("98.0 mm/s")
    await user.should_see("8.10 V")
    await user.should_see("medido")
    await user.should_see("estimado")
    await user.should_not_see(INDISPONIVEL)


async def test_marca_desconexao_sem_apagar_ultimos_valores(user: User):
    estado = EstadoPainel()
    criar_pagina(estado, fonte_simulada=False, intervalo_s=0.1)
    await user.open("/")
    estado.link_aberto("teste")
    estado.registrar(criar_frame(1))
    await esperar_renderizacao()
    estado.link_fechado("cabo solto")
    await esperar_renderizacao()
    await user.should_see("desconectado")
    await user.should_see("Valores congelados")
    await user.should_see("98.0 mm/s")


async def test_falha_aparece_no_log(user: User):
    estado = EstadoPainel()
    criar_pagina(estado, fonte_simulada=False, intervalo_s=0.1)
    await user.open("/")
    falha = Falha(code="ENCODER_STALL", message="Encoder esquerdo parado")
    estado.registrar(criar_frame(1, evento="fault", falha=falha))
    await esperar_renderizacao()
    log = user.find(ui.log).elements.pop()
    assert any("ENCODER_STALL" in linha.text for linha in log.descendants())


async def test_link_do_historico_so_aparece_com_banco(user: User):
    criar_pagina(EstadoPainel(), fonte_simulada=False, intervalo_s=0.1, historico=True)
    await user.open("/")
    await user.should_see("Histórico")


async def test_mapa_ao_vivo_mostra_o_que_chega(user: User):
    from telemetria.gerador import gerar_frames

    estado = EstadoPainel()
    criar_pagina(estado, fonte_simulada=True, intervalo_s=0.1)
    await user.open("/")
    await user.should_see("Mapa descoberto")
    for frame in list(gerar_frames(5, 10, 300, navegacao=True))[:30]:
        estado.registrar(frame)
    await esperar_renderizacao()
    graficos = [g for g in user.find(ui.plotly).elements if "uirevision" in g.figure["layout"]]
    mapa = next(g for g in graficos if g.figure["layout"]["uirevision"] == "mapa")
    assert any(traco["name"].startswith("Robô") for traco in mapa.figure["data"])
