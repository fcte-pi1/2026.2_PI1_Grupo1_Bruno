"""FW02 - Contratos mínimos da camada de abstração de hardware.

Compatível com Python 3 e MicroPython. As classes não dependem de `abc`,
para manter o código simples no microcontrolador.
"""


class MotorInterface:
    """Interface mínima para atuação de um par de motores."""

    def set_power(self, left, right):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class EncoderInterface:
    """Interface mínima para leitura dos encoders."""

    def read_counts(self):
        """Retorna (pulsos_esquerdo, pulsos_direito)."""
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class DistanceSensorInterface:
    """Interface para um sensor de distância."""

    def read_cm(self):
        """Retorna distância em cm ou None em falha/timeout."""
        raise NotImplementedError


class IMUInterface:
    """Interface mínima para uma IMU, quando houver hardware definido."""

    def read_yaw_deg(self):
        """Retorna yaw em graus ou None quando indisponível."""
        raise NotImplementedError
