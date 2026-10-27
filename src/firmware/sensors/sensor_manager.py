"""FW06 - Leitura sequencial, validação e filtro dos sensores."""


class SensorReading:
    def __init__(self, distance_cm=None, valid=False, reason=None):
        self.distance_cm = distance_cm
        self.valid = bool(valid)
        self.reason = reason


class SensorManager:
    """Gerencia sensores frente/direita/trás/esquerda.

    As leituras são feitas uma por vez para reduzir interferência entre os
    ultrassônicos. `read_samples` usa mediana simples para rejeitar uma leitura
    isolada fora do padrão.
    """

    ORDER = ("front", "right", "back", "left")

    def __init__(self, sensors, min_cm=2.0, max_cm=400.0, samples=3):
        self.sensors = dict(sensors)
        self.min_cm = float(min_cm)
        self.max_cm = float(max_cm)
        self.samples = max(1, int(samples))

    def _valid_value(self, value):
        return value is not None and self.min_cm <= float(value) <= self.max_cm

    @staticmethod
    def _median(values):
        ordered = sorted(values)
        n = len(ordered)
        middle = n // 2
        if n % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2.0

    def read_one(self, name):
        sensor = self.sensors.get(name)
        if sensor is None:
            return SensorReading(None, False, "sensor_indisponivel")

        valid = []
        for _ in range(self.samples):
            value = sensor.read_cm()
            if self._valid_value(value):
                valid.append(float(value))

        if not valid:
            return SensorReading(None, False, "timeout_ou_fora_da_faixa")

        return SensorReading(self._median(valid), True, None)

    def read_all(self):
        result = {}
        for name in self.ORDER:
            result[name] = self.read_one(name)
        return result

    def calibrate_offsets(self, reference_cm, samples=5):
        """Calcula offset aditivo por sensor usando uma distância conhecida.

        Retorna dicionário de offsets. A aplicação física do offset é deixada
        explícita para a equipe poder registrar os valores medidos em bancada.
        """
        offsets = {}
        old_samples = self.samples
        self.samples = max(1, int(samples))
        try:
            for name in self.ORDER:
                reading = self.read_one(name)
                if reading.valid:
                    offsets[name] = float(reference_cm) - reading.distance_cm
                else:
                    offsets[name] = None
        finally:
            self.samples = old_samples
        return offsets
