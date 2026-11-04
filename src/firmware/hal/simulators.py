"""FW02 - Componentes falsos usados para testes sem o carrinho físico."""

from .interfaces import (
    MotorInterface,
    EncoderInterface,
    DistanceSensorInterface,
    IMUInterface,
)


class SimMotorDriver(MotorInterface):
    def __init__(self):
        self.left = 0.0
        self.right = 0.0
        self.history = []

    @staticmethod
    def _clamp(value):
        value = float(value)
        if value > 1.0:
            return 1.0
        if value < -1.0:
            return -1.0
        return value

    def set_power(self, left, right):
        self.left = self._clamp(left)
        self.right = self._clamp(right)
        self.history.append((self.left, self.right))

    def stop(self):
        self.left = 0.0
        self.right = 0.0
        self.history.append((0.0, 0.0))


class SimEncoder(EncoderInterface):
    def __init__(self, left=0, right=0):
        self.left = int(left)
        self.right = int(right)

    def read_counts(self):
        return (self.left, self.right)

    def add_counts(self, left=0, right=0):
        self.left += int(left)
        self.right += int(right)

    def reset(self):
        self.left = 0
        self.right = 0


class SimDistanceSensor(DistanceSensorInterface):
    """Sensor falso com sequência programável de leituras.

    Valores `None` simulam timeout/leitura inválida. Quando a sequência termina,
    a última leitura é repetida.
    """

    def __init__(self, readings=None, default=100.0):
        self.readings = list(readings or [])
        self.default = default
        self.index = 0

    def read_cm(self):
        if not self.readings:
            return self.default
        if self.index >= len(self.readings):
            return self.readings[-1]
        value = self.readings[self.index]
        self.index += 1
        return value


class SimIMU(IMUInterface):
    def __init__(self, yaw_deg=0.0):
        self.yaw_deg = yaw_deg
        self.valid = True

    def set_yaw_deg(self, yaw_deg):
        self.yaw_deg = float(yaw_deg)
        self.valid = True

    def set_invalid(self):
        self.valid = False

    def read_yaw_deg(self):
        if not self.valid:
            return None
        return self.yaw_deg
