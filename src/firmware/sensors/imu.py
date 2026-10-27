"""FW06 - Adaptação genérica de IMU.

O modelo físico da IMU ainda deve ser definido pela equipe. Esta classe recebe
um `reader` externo e aplica calibração de zero, permitindo integrar o modelo
escolhido sem acoplar o restante do firmware a uma biblioteca específica.
"""


class IMUAdapter:
    def __init__(self, reader):
        self.reader = reader
        self.offset_deg = 0.0
        self.calibrated = False

    def calibrate_zero(self, samples=10):
        values = []
        for _ in range(int(samples)):
            value = self.reader()
            if value is not None:
                values.append(float(value))
        if not values:
            self.calibrated = False
            return False
        self.offset_deg = sum(values) / len(values)
        self.calibrated = True
        return True

    def read_yaw_deg(self):
        value = self.reader()
        if value is None:
            return None
        return (float(value) - self.offset_deg) % 360.0
