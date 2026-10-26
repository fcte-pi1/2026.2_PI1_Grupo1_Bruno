"""FW03: duty independente, rampa e intertravamento de reversao.

Nao controla velocidade: isso depende de encoders e da FW05 (#7).
O chamador fornece dt_ms medido (ticks_diff no MicroPython).
"""

from math import isfinite


def numero(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor):
        raise ValueError("valor deve ser numerico e finito")
    return valor


def sinal(valor):
    return 1 if valor > 0 else -1 if valor < 0 else 0


class Motores:
    def __init__(self, driver, max_duty=0.5, rampa_por_segundo=1.0,
                 deadband=0.0, pausa_reversao_ms=100, max_dt_ms=100):
        self.driver = driver
        self.habilitado = False
        self._alvo = [0.0, 0.0]
        self._saida = [0.0, 0.0]
        self._sentido = [0, 0]
        self._zero_ms = [0, 0]
        driver.disable()
        if not 0 < numero(max_duty) <= 1:
            raise ValueError("max_duty deve estar em (0, 1]")
        if numero(rampa_por_segundo) <= 0:
            raise ValueError("rampa deve ser positiva")
        if not 0 <= numero(deadband) < max_duty:
            raise ValueError("deadband deve estar em [0, max_duty)")
        if numero(pausa_reversao_ms) <= 0 or numero(max_dt_ms) <= 0:
            raise ValueError("tempos devem ser positivos")
        self.max_duty = max_duty
        self.rampa = rampa_por_segundo
        self.deadband = deadband
        self.pausa = pausa_reversao_ms
        self.max_dt = max_dt_ms

    @property
    def saidas(self):
        return tuple(self._saida)

    def enable(self):
        # Repetir enable durante movimento nao reinicia o intertravamento.
        if self.habilitado:
            return
        try:
            self.driver.write(0, 0)
            self.driver.enable()
            self.habilitado = True
        except BaseException:
            self.stop()
            raise

    def stop(self):
        """Parada imediata, sem rampa. Nova partida exige enable explicito."""
        self.habilitado = False
        self._alvo = [0.0, 0.0]
        self._saida = [0.0, 0.0]
        # Preserva o ultimo sentido: stop/enable nao pode burlar a pausa.
        self._zero_ms = [0, 0]
        self.driver.disable()

    def set_output(self, left, right):
        """Recebe duty assinado; limita amplitude, sem escrever GPIOs aqui."""
        try:
            valores = (numero(left), numero(right))
            if not self.habilitado:
                raise RuntimeError("chame enable antes de set_output")
            self._alvo = [max(-self.max_duty, min(self.max_duty, v)) for v in valores]
            self._alvo = [0.0 if abs(v) < self.deadband else v for v in self._alvo]
        except BaseException:
            self.stop()
            raise

    def update(self, dt_ms):
        """Chamar periodicamente. Atrasos invalidos desabilitam os dois motores."""
        try:
            if not 0 < numero(dt_ms) <= self.max_dt:
                raise ValueError("dt_ms invalido ou ciclo atrasado")
            if not self.habilitado:
                return self.saidas
            passo = self.rampa * dt_ms / 1000.0
            for i in (0, 1):
                atual, alvo = self._saida[i], self._alvo[i]
                if atual == 0:
                    self._zero_ms[i] += dt_ms
                if sinal(alvo) and self._sentido[i] and sinal(alvo) != self._sentido[i]:
                    if atual != 0 or self._zero_ms[i] < self.pausa:
                        alvo = 0.0
                novo = atual + max(-passo, min(passo, alvo - atual))
                if novo != 0:
                    self._sentido[i] = sinal(novo)
                    self._zero_ms[i] = 0
                self._saida[i] = novo
            self.driver.write(*self._saida)
            return self.saidas
        except BaseException:
            self.stop()
            raise
