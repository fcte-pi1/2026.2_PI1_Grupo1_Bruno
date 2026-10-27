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


def test_boot_antigo_atrasado_nao_reverte_boot_atual(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(40))
    estado.link_fechado("perda")
    estado.link_aberto("reconexão")
    estado.registrar(criar_frame(1, boot_id="boot-b"))
    assert not estado.registrar(criar_frame(41, boot_id="boot-a"))
    assert estado.ultimo_frame.boot_id == "boot-b"
    assert len(estado.amostras) == 1


def test_run_antigo_nao_mistura_mesmo_com_seq_maior(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(1))
    estado.registrar(criar_frame(2, run_id="run-002"))
    assert not estado.registrar(criar_frame(3, run_id="run-001"))
    assert estado.registrar(criar_frame(4, run_id="run-002"))
    assert len(estado.amostras) == 2
    assert estado.ultimo_frame.run_id == "run-002"


def test_run_apos_idle_permanece_encerrado(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(1))
    estado.registrar(criar_frame(2, run_id=None))
    assert not estado.registrar(criar_frame(3, run_id="run-001"))


def test_finish_e_terminal_mesmo_apos_reconexao(relogio):
    estado = EstadoPainel(relogio=relogio)
    assert estado.registrar(criar_frame(1, evento="start"))
    assert estado.registrar(criar_frame(2, evento="finish"))
    estado.link_fechado("fim do link")
    estado.link_aberto("reconexão")
    assert not estado.registrar(criar_frame(3, evento="start"))
    assert not estado.registrar(criar_frame(4))
    assert estado.ultimo_frame.event == "finish"
    assert estado.registrar(criar_frame(5, run_id=None))
    assert not estado.registrar(criar_frame(6))
    assert estado.registrar(criar_frame(7, run_id="run-002", evento="start"))


def test_tempo_regredindo_e_robo_diferente_nao_atualizam_rx(relogio):
    estado = EstadoPainel(relogio=relogio)
    estado.registrar(criar_frame(1, t_ms=100))
    relogio.avancar(3)
    assert not estado.registrar(criar_frame(2, t_ms=99))
    outro = criar_frame(2, t_ms=100).model_copy(update={"robot_id": "outro-robo"})
    assert not estado.registrar(outro)
    assert estado.conexao() is Conexao.DESATUALIZADO
    assert estado.descartados == 2


def test_historico_de_epocas_e_limitado_e_nao_esquece_anti_replay(relogio):
    estado = EstadoPainel(max_epocas=1, relogio=relogio)
    estado.registrar(criar_frame(1))
    assert estado.registrar(criar_frame(2, run_id="run-002"))
    assert not estado.registrar(criar_frame(3, run_id="run-003"))
    assert estado.registrar(criar_frame(1, boot_id="boot-b"))
    assert not estado.registrar(criar_frame(1, boot_id="boot-c"))
    assert not estado.registrar(criar_frame(4, boot_id="boot-a"))
