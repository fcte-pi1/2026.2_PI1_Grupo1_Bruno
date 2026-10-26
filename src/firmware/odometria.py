"""FW04: contagem de quadratura e odometria diferencial, sem acesso a GPIOs."""

from math import cos, isfinite, pi, sin

try:
    from time import ticks_diff
except ImportError:
    def ticks_diff(atual, anterior):
        return atual - anterior


def _positivo(valor):
    if not isfinite(valor) or valor <= 0:
        raise ValueError("geometria e contagens por volta devem ser positivas e finitas")
    return valor


def _inteiro(valor):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError("contadores e tempo devem ser inteiros")
    return valor


def _delta(atual, anterior, modulo):
    delta = atual - anterior
    if modulo is not None:
        delta = (delta + modulo // 2) % modulo - modulo // 2
        if abs(delta) * 2 == modulo:
            raise ValueError("deslocamento ambiguo: metade do contador")
    return delta


class Amostra:
    """Intervalo válido; distâncias em mm, velocidades em mm/s e ângulo em rad."""

    def __init__(self, dt_ms, esquerda_mm, direita_mm, x_mm, y_mm, theta_rad):
        self.dt_ms = dt_ms
        self.esquerda_mm = esquerda_mm
        self.direita_mm = direita_mm
        self.velocidade_esquerda = esquerda_mm * 1000 / dt_ms
        self.velocidade_direita = direita_mm * 1000 / dt_ms
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.theta_rad = theta_rad


class Odometria:
    """Recebe snapshots cumulativos dos encoders e do relógio em milissegundos.

    As contagens por volta são efetivas NA RODA, incluindo redução e bordas.
    Com módulo, cada delta precisa ser estritamente menor que módulo/2.
    O intervalo do relógio também deve respeitar o limite de ticks_diff.
    """

    def __init__(self, diametro_esquerdo_mm, diametro_direito_mm,
                 contagens_por_volta_esquerda, contagens_por_volta_direita,
                 distancia_rodas_mm, polaridade_esquerda=1,
                 polaridade_direita=1, modulo_contador=None,
                 diferenca_tempo=ticks_diff):
        self.mm_por_contagem_esquerda = (
            pi * _positivo(diametro_esquerdo_mm)
            / _positivo(contagens_por_volta_esquerda)
        )
        self.mm_por_contagem_direita = (
            pi * _positivo(diametro_direito_mm)
            / _positivo(contagens_por_volta_direita)
        )
        self.distancia_rodas_mm = _positivo(distancia_rodas_mm)
        for sinal in (polaridade_esquerda, polaridade_direita):
            if isinstance(sinal, bool) or sinal not in (-1, 1):
                raise ValueError("polaridade deve ser -1 ou 1")
        if modulo_contador is not None:
            _inteiro(modulo_contador)
            if modulo_contador < 4 or modulo_contador % 2:
                raise ValueError("modulo deve ser par e maior ou igual a 4")
        self.polaridade_esquerda = polaridade_esquerda
        self.polaridade_direita = polaridade_direita
        self.modulo_contador = modulo_contador
        self.diferenca_tempo = diferenca_tempo
        self.x_mm = self.y_mm = self.theta_rad = 0.0
        self.distancia_esquerda_mm = self.distancia_direita_mm = 0.0
        self._anterior = None

    def rebasear(self, esquerda, direita, t_ms):
        """Após reset conhecido de contador/clock, preserva pose e distâncias."""
        self._anterior = (_inteiro(esquerda), _inteiro(direita), _inteiro(t_ms))

    def atualizar(self, esquerda, direita, t_ms):
        atual = (_inteiro(esquerda), _inteiro(direita), _inteiro(t_ms))
        if self._anterior is None:
            self._anterior = atual
            return None
        ae, ad, tempo = self._anterior
        dt_ms = self.diferenca_tempo(t_ms, tempo)
        if dt_ms <= 0:
            raise ValueError("intervalo deve ser positivo; confira clock/reset")
        de = (_delta(esquerda, ae, self.modulo_contador)
              * self.mm_por_contagem_esquerda * self.polaridade_esquerda)
        dd = (_delta(direita, ad, self.modulo_contador)
              * self.mm_por_contagem_direita * self.polaridade_direita)
        ds = (de + dd) / 2
        dtheta = (dd - de) / self.distancia_rodas_mm
        # Arco exato sob velocidade constante entre as duas amostras.
        meia = dtheta / 2
        escala = sin(meia) / meia if abs(meia) > 1e-9 else 1.0
        direcao = self.theta_rad + meia
        self.x_mm += ds * escala * cos(direcao)
        self.y_mm += ds * escala * sin(direcao)
        self.theta_rad = (self.theta_rad + dtheta + pi) % (2 * pi) - pi
        self.distancia_esquerda_mm += de
        self.distancia_direita_mm += dd
        self._anterior = atual
        return Amostra(dt_ms, de, dd, self.x_mm, self.y_mm, self.theta_rad)


class EncoderQuadratura:
    """Decodificador x4 para testes/adaptador de bordas A/B.

    Não garante captura por IRQ em alta frequência. Preferir Encoder/PCNT
    quando confirmado na placa. Transições com dois bits são descartadas.
    """

    _PASSOS = (0, 1, -1, 0, -1, 0, 0, 1, 1, 0, 0, -1, 0, -1, 1, 0)

    def __init__(self, a=0, b=0):
        self._estado = self._bits(a, b)
        self.contagem = 0
        self.transicoes_invalidas = 0

    @staticmethod
    def _bits(a, b):
        if a not in (0, 1) or b not in (0, 1):
            raise ValueError("canais A/B devem ser 0 ou 1")
        return (a << 1) | b

    def atualizar(self, a, b):
        estado = self._bits(a, b)
        if self._estado ^ estado == 3:
            self.transicoes_invalidas += 1
        else:
            self.contagem += self._PASSOS[(self._estado << 2) | estado]
        self._estado = estado
        return self.contagem

    def read(self):
        return self.contagem
