from telemetria.coleta import coletar
from telemetria.estado import Conexao, EstadoPainel
from telemetria.fonte_simulada import FonteSimulada, perfil_alvo
from telemetria.modelos import Frame, LinkAberto, LinkFechado


async def sem_espera(_segundos: float) -> None:
    return None


async def primeiros_eventos(fonte: FonteSimulada, quantidade: int) -> list:
    eventos = []
    async for evento in fonte.eventos():
        eventos.append(evento)
        if len(eventos) == quantidade:
            break
    return eventos


def fonte_rapida(**kwargs) -> FonteSimulada:
    return FonteSimulada(dormir=sem_espera, **kwargs)


async def test_comeca_abrindo_link_e_iniciando_execucao():
    eventos = await primeiros_eventos(fonte_rapida(), 3)
    assert isinstance(eventos[0], LinkAberto)
    assert isinstance(eventos[1], Frame) and eventos[1].event == "start"
    assert eventos[2].event in {"sample", "fault"}


async def test_mesma_seed_gera_mesmos_frames():
    a = await primeiros_eventos(fonte_rapida(seed=3), 200)
    b = await primeiros_eventos(fonte_rapida(seed=3), 200)
    assert a == b


async def test_sequencia_sempre_cresce_e_todos_sao_simulados():
    eventos = await primeiros_eventos(fonte_rapida(), 3000)
    frames = [e for e in eventos if isinstance(e, Frame)]
    seqs = [f.seq for f in frames]
    assert seqs == sorted(set(seqs))
    for frame in frames:
        assert frame.battery_voltage.source == "simulated"
        assert all(s.source == "simulated" for s in frame.sensors.values())


async def test_alterna_queda_silenciosa_e_queda_de_link_sem_trocar_execucao():
    fonte = fonte_rapida(intervalo_queda_s=10.0, duracao_queda_s=2.0, duracao_execucao_s=60.0)
    eventos = await primeiros_eventos(fonte, 900)
    fechados = [i for i, e in enumerate(eventos) if isinstance(e, LinkFechado)]
    assert fechados
    i = fechados[0]
    assert isinstance(eventos[i + 1], LinkAberto)
    antes = next(e for e in reversed(eventos[:i]) if isinstance(e, Frame))
    depois = eventos[i + 2]
    assert depois.run_id == antes.run_id
    assert depois.seq > antes.seq + 1


async def test_gera_leituras_ausentes_e_falhas():
    eventos = await primeiros_eventos(fonte_rapida(), 6000)
    frames = [e for e in eventos if isinstance(e, Frame)]
    assert any(s.value is None for f in frames for s in f.sensors.values())
    assert any(f.event == "fault" and f.fault is not None for f in frames)


async def test_encerra_e_inicia_nova_execucao():
    eventos = await primeiros_eventos(fonte_rapida(duracao_execucao_s=5.0, intervalo_queda_s=1000.0), 300)
    frames = [e for e in eventos if isinstance(e, Frame)]
    assert any(f.event == "finish" for f in frames)
    assert len({f.run_id for f in frames}) >= 2


def test_perfil_tem_reta_parada_e_giro():
    assert perfil_alvo(1.0) == (300.0, 300.0)
    assert perfil_alvo(3.5) == (0.0, 0.0)
    assert perfil_alvo(4.5) == (150.0, -150.0)


class FonteLista:
    simulada = True
    nome = "lista"

    def __init__(self, eventos):
        self._eventos = eventos

    async def eventos(self):
        for evento in self._eventos:
            yield evento


async def test_coleta_aplica_eventos_no_estado():
    eventos = await primeiros_eventos(fonte_rapida(), 50)
    estado = EstadoPainel()
    await coletar(FonteLista(eventos), estado)
    assert estado.conexao() is Conexao.CONECTADO
    assert estado.ultimo_frame.seq == eventos[-1].seq
    await coletar(FonteLista([LinkFechado("teste")]), estado)
    assert estado.conexao() is Conexao.DESCONECTADO
