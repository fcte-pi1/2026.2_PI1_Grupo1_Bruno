"""Pinagem confirmada pela planilha. Unidades: mm, ms, PWM de 0 a 1.

Nao preencher calibracoes por estimativa. Contagens usam Encoder phases=4,
nao sao equivalentes as contagens de transicoes de um canal dos testes antigos.
"""
MOTOR_PINS = ((16, 17), (18, 8))
ENCODER_PINS = ((11, 12), (14, 13))
SENSOR_PINS = {'front': (35, 36), 'back': (37, 38),
               'right': (39, 40), 'left': (41, 42)}
BUTTON_PIN = 0  # BOOT: nao segurar durante reset/energizacao.
PWM_HZ = 1000
MAX_PWM = 0.50
DRIVE_PWM = 0.45
TURN_PWM = 0.40
RAMP_PER_SECOND = 0.8
BALANCE_KP = 0.001
MAX_BALANCE = 0.08
ENCODER_FILTER_NS = 1000
ENCODER_SIGNS = (1, 1)  # Ajustar para que ambos aumentem ao avancar.
MOTOR_SIGNS = (1, 1)

# Travas de liberacao: todas precisam ser verificadas fisicamente.
STABLE_CHASSIS = False
CALIBRATED = False
COUNTS_PER_MM = (None, None)
TURN_90_COUNTS = (None, None)  # giro no proprio eixo, por roda, phases=4
TURN_CLEARANCE_MM = None  # folga MINIMA lida em cada sensor para girar
FRONT_STOP_MM = 150
START_CLEARANCE_MM = 200
WALL_MM = 180  # somente modo grade; ajustar conforme celula/posicao dos sensores
WALL_HYST_MM = 15
CELL_MM = 180
CENTER_FRONT_WALL_MM = None  # distancia frontal a parede estando no centro da celula
STEP_MM = 40  # passo curto do modo patrulha; nao representa uma celula
SENSOR_MIN_MM = 20
SENSOR_MAX_MM = 3000
PING_GAP_MS = 65  # nenhum ultrassom dispara simultaneamente com outro
PING_TIMEOUT_US = 20000
SCAN_SPREAD_MM = 40
STALL_MS = 350
MOVE_TIMEOUT_MS = 3000
RUN_TIMEOUT_MS = 60000
MAX_ACTIONS = 100
MAX_CELLS = 256
SETTLE_MS = 150
WATCHDOG_MS = 2000
MODE = 'patrol'  # patrol ou explore

# Saida nao e inferida de 'sem eco'. Na pista fechada, nao ha saida.
# Para um futuro labirinto em grade, informar uma CELULA-OBJETIVO relativa ao
# inicio (0,0), eixo +y = direcao inicial. O robo para nela, nao cruza uma borda.
GOAL_CELL = None


def validate_motion():
    if not STABLE_CHASSIS:
        raise ValueError('Corrigir estabilidade e marcar STABLE_CHASSIS primeiro.')
    if not CALIBRATED:
        raise ValueError('Calibracao fisica ainda pendente.')
    for value in COUNTS_PER_MM + TURN_90_COUNTS + (TURN_CLEARANCE_MM,):
        if value is None or not 0 < value < 1000000:
            raise ValueError('Medidas de calibracao ausentes ou invalidas.')
    if ENCODER_SIGNS not in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        raise ValueError('ENCODER_SIGNS invalidos.')
    if MOTOR_SIGNS not in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        raise ValueError('MOTOR_SIGNS invalidos.')
    if not 0 < TURN_PWM <= MAX_PWM <= 0.5 or not 0 < DRIVE_PWM <= MAX_PWM:
        raise ValueError('PWM fora do limite de bancada.')
    if not 0 < FRONT_STOP_MM < START_CLEARANCE_MM:
        raise ValueError('Limiares de distancia invalidos.')
    if not all(v > 0 for v in (STEP_MM, CELL_MM, STALL_MS, MOVE_TIMEOUT_MS,
                               RUN_TIMEOUT_MS, MAX_ACTIONS, MAX_CELLS,
                               RAMP_PER_SECOND, PING_GAP_MS)):
        raise ValueError('Limites devem ser positivos.')


def validate_grid():
    # Evita tentar completar uma celula cujo ponto final viola a distancia
    # minima frontal. Ajustar somente apos medir frenagem/geometria reais.
    if CENTER_FRONT_WALL_MM is None or CENTER_FRONT_WALL_MM <= FRONT_STOP_MM:
        raise ValueError('Medir folga frontal no centro da celula e calibrar parada antes de explore.')
    if not CENTER_FRONT_WALL_MM + WALL_HYST_MM < WALL_MM < CENTER_FRONT_WALL_MM + CELL_MM - WALL_HYST_MM:
        raise ValueError('Limiar de parede nao separa parede proxima da proxima celula.')
