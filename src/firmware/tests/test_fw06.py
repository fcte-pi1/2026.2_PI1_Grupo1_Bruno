"""Testes da FW06 - Sensores e IMU."""

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.dirname(THIS_DIR)
if FIRMWARE_DIR not in sys.path:
    sys.path.insert(0, FIRMWARE_DIR)

from sensors.sensor_manager import SensorManager  # noqa: E402
from sensors.imu import IMUAdapter  # noqa: E402


class FakeSensor:
    def __init__(self, values):
        self.values = list(values)
        self.index = 0

    def read_cm(self):
        if self.index >= len(self.values):
            return self.values[-1]
        value = self.values[self.index]
        self.index += 1
        return value


class TestFW06(unittest.TestCase):
    def test_mediana_rejeita_leitura_isolada(self):
        sensors = {"front": FakeSensor([10.0, 250.0, 11.0])}
        manager = SensorManager(sensors, samples=3)
        reading = manager.read_one("front")
        self.assertTrue(reading.valid)
        self.assertEqual(reading.distance_cm, 11.0)

    def test_timeout_retorna_invalido(self):
        sensors = {"front": FakeSensor([None, None, None])}
        manager = SensorManager(sensors, samples=3)
        reading = manager.read_one("front")
        self.assertFalse(reading.valid)
        self.assertIsNone(reading.distance_cm)

    def test_fora_da_faixa_retorna_invalido(self):
        sensors = {"front": FakeSensor([0.5, 500.0, None])}
        manager = SensorManager(sensors, min_cm=2.0, max_cm=400.0, samples=3)
        self.assertFalse(manager.read_one("front").valid)

    def test_leitura_sequencial_das_quatro_posicoes(self):
        sensors = {
            "front": FakeSensor([10, 10, 10]),
            "right": FakeSensor([20, 20, 20]),
            "back": FakeSensor([30, 30, 30]),
            "left": FakeSensor([40, 40, 40]),
        }
        values = SensorManager(sensors, samples=3).read_all()
        self.assertEqual(values["front"].distance_cm, 10.0)
        self.assertEqual(values["right"].distance_cm, 20.0)
        self.assertEqual(values["back"].distance_cm, 30.0)
        self.assertEqual(values["left"].distance_cm, 40.0)

    def test_calibracao_imu_remove_zero_inicial(self):
        values = [30.0] * 10 + [45.0]

        def reader():
            return values.pop(0)

        imu = IMUAdapter(reader)
        self.assertTrue(imu.calibrate_zero(10))
        self.assertEqual(imu.read_yaw_deg(), 15.0)

    def test_imu_invalida_sem_amostras(self):
        imu = IMUAdapter(lambda: None)
        self.assertFalse(imu.calibrate_zero(3))
        self.assertIsNone(imu.read_yaw_deg())


if __name__ == "__main__":
    unittest.main(verbosity=2)
