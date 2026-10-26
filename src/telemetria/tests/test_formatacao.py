from conftest import leitura

from telemetria.formatacao import (
    INDISPONIVEL,
    INVALIDA,
    SEM_LEITURA,
    texto_leitura,
    texto_origem,
    texto_tempo,
    valor_numerico,
)


def test_campo_ausente_aparece_como_indisponivel():
    assert texto_leitura(None) == INDISPONIVEL


def test_leitura_sem_valor_nao_vira_zero():
    assert texto_leitura(leitura(None)) == SEM_LEITURA
    assert valor_numerico(leitura(None)) is None


def test_leitura_invalida_e_sinalizada():
    assert texto_leitura(leitura(12.0, valida=False)) == INVALIDA
    assert valor_numerico(leitura(12.0, valida=False)) is None


def test_zero_medido_continua_zero():
    assert texto_leitura(leitura(0.0)) == "0.0 mm/s"
    assert valor_numerico(leitura(0.0)) == 0.0


def test_casas_decimais():
    assert texto_leitura(leitura(8.137, "V"), casas=2) == "8.14 V"


def test_origem_em_portugues():
    assert texto_origem(leitura(1.0, origem="simulated")) == "simulado"
    assert texto_origem(leitura(1.0, origem="measured")) == "medido"
    assert texto_origem(leitura(1.0, origem="estimated")) == "estimado"
    assert texto_origem(None) == ""


def test_tempo_do_robo():
    assert texto_tempo(0) == "00:00.0"
    assert texto_tempo(65_432) == "01:05.4"
