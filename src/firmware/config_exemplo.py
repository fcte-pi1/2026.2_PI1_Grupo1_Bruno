"""Copiar para config_local.py apenas apos alinhamento com Hardware (#22)."""

# TODO(INT02/#22): confirmar modelo da placa, driver, GPIOs e tabela verdade.
# Nao reutilizar pinagem do semestre anterior. None impede acesso ao hardware.
HARDWARE = None

# Valores SOMENTE de simulacao; nao representam calibracao dos motores reais.
CONTROLE = {
    "max_duty": 0.5,           # duty normalizado, entre 0 e 1
    "rampa_por_segundo": 1.0,
    "deadband": 0.0,           # abaixo deste duty, saida zero (sem impulso minimo)
    "pausa_reversao_ms": 100,
    "max_dt_ms": 100,          # atraso maior interrompe e exige nova habilitacao
}
