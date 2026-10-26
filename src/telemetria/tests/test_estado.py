from conftest import criar_frame

from telemetria.estado import Conexao, EstadoPainel
from telemetria.modelos import Falha


def test_comeca_aguardando(relogio):
    estado = EstadoPainel(relogio=relogio)
    assert estado.conexao() is Conexao.AGUARDANDO
    assert estado.segundos_desde_ultima_mensagem() is None


def test_link_aberto_sem_mensagem_continua_aguardando(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.link_aberto("teste")
    assert estado.conexao() is Conexao.AGUARDANDO


def test_transicoes_por_tempo_sem_mensagens(relogio):
    estado = EstadoPainel(limite_desatualizado_s=2.0, limite_desconectado_s=5.0, relogio=relogio)
    estado.link_aberto("teste")
    estado.registrar(criar_frame(1))
    assert estado.conexao() is Conexao.CONECTADO

    relogio.avancar(2.5)
    assert estado.conexao() is Conexao.DESATUALIZADO

    relogio.avancar(3.0)
    assert estado.conexao() is Conexao.DESCONECTADO

    estado.registrar(criar_frame(2))
    assert estado.conexao() is Conexao.CONECTADO


def test_link_fechado_desconecta_na_hora_e_mantem_ultimo_frame(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.link_aberto("teste")
    estado.registrar(criar_frame(1))
    estado.link_fechado("cabo solto")
    assert estado.conexao() is Conexao.DESCONECTADO
    assert estado.ultimo_frame is not None
    assert estado.log[-1].nivel == "aviso"


def test_descarta_duplicado_e_fora_de_ordem(relogio):
    estado = EstadoPainel(relogio=relogio)
    assert estado.registrar(criar_frame(5))
    assert not estado.registrar(criar_frame(5))
    assert not estado.registrar(criar_frame(3))
    assert estado.registrar(criar_frame(6))
    assert estado.descartados == 2
    assert estado.ultimo_frame.seq == 6


def test_novo_boot_reinicia_sequencia_e_limpa_grafico(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(40))
    estado.registrar(criar_frame(41))
    assert estado.registrar(criar_frame(1, boot_id="boot-b"))
    assert len(estado.amostras) == 1
    assert "Novo boot" in estado.log[-1].texto


def test_nova_execucao_nao_mistura_amostras(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(1, run_id="run-001"))
    estado.registrar(criar_frame(2, run_id="run-001"))
    estado.registrar(criar_frame(3, run_id="run-002", evento="start"))
    assert len(estado.amostras) == 1
    assert estado.ultimo_frame.run_id == "run-002"


def test_janela_limita_amostras_pelo_tempo_do_robo(relogio):
    estado = EstadoPainel(janela_s=30.0, relogio=relogio)
    for seq in range(1, 801):
        estado.registrar(criar_frame(seq, t_ms=seq * 50))
    amostras = estado.amostras_na_janela()
    assert amostras[-1].t_s - amostras[0].t_s <= 30.0
    assert len(amostras) == 601


def test_leitura_ausente_vira_lacuna_e_nao_zero(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(1, velocidade_esquerda=None))
    assert estado.amostras[-1].esquerda is None


def test_falha_entra_no_log_como_erro(relogio):
    estado = EstadoPainel(relogio=relogio)
    falha = Falha(code="ENCODER_STALL", message="Encoder esquerdo parado")
    estado.registrar(criar_frame(1, evento="fault", falha=falha))
    assert estado.log[-1].nivel == "erro"
    assert "ENCODER_STALL" in estado.log[-1].texto


def test_numeracao_do_log_cresce(relogio):
    estado = EstadoPainel(max_log=2, relogio=relogio)
    for i in range(4):
        estado.link_aberto(str(i))
    assert [r.numero for r in estado.log] == [3, 4]
