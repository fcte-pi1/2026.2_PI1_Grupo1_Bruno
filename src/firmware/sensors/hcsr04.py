"""FW06 - Driver HC-SR04 para MicroPython.

A pinagem é recebida no construtor e não é fixada aqui. Isso evita assumir uma
ligação elétrica que deve ser confirmada com Hardware/Energia.
"""

try:
    from machine import Pin, time_pulse_us
    from time import sleep_us
except ImportError:  # execução no PC para testes
    Pin = None
    time_pulse_us = None
    sleep_us = None


class HCSR04:
    SPEED_OF_SOUND_CM_PER_US = 0.0343

    def __init__(self, trigger_pin, echo_pin, timeout_us=30000, pin_factory=None, pulse_reader=None):
        self.timeout_us = int(timeout_us)
        self._pulse_reader = pulse_reader if pulse_reader is not None else time_pulse_us

        factory = pin_factory if pin_factory is not None else Pin
        if factory is None:
            raise RuntimeError("machine.Pin indisponível; injete pin_factory no teste")

        self.trigger = factory(trigger_pin, factory.OUT)
        self.echo = factory(echo_pin, factory.IN)
        self.trigger.value(0)

    def read_cm(self):
        self.trigger.value(0)
        if sleep_us is not None:
            sleep_us(2)
        self.trigger.value(1)
        if sleep_us is not None:
            sleep_us(10)
        self.trigger.value(0)

        if self._pulse_reader is None:
            return None

        try:
            pulse = self._pulse_reader(self.echo, 1, self.timeout_us)
        except (OSError, ValueError):
            return None

        if pulse is None or pulse <= 0:
            return None
        return pulse * self.SPEED_OF_SOUND_CM_PER_US / 2.0
