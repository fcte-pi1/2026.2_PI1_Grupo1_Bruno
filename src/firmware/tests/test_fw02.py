"""Testes da FW02 - HAL e simuladores."""

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.dirname(THIS_DIR)
if FIRMWARE_DIR not in sys.path:
    sys.path.insert(0, FIRMWARE_DIR)

from hal.simulators import SimMotorDriver, SimEncoder, SimDistanceSensor, SimIMU  # noqa: E402


class TestFW02(unittest.TestCase):
    def test_motor_limita_comandos_e_para(self):
        motor = SimMotorDriver()
        motor.set_power(2.0, -2.0)
        self.assertEqual((motor.left, motor.right), (1.0, -1.0))
        motor.stop()
        self.assertEqual((motor.left, motor.right), (0.0, 0.0))

    def test_encoder_acumula_e_reseta(self):
        encoder = SimEncoder()
        encoder.add_counts(15, 12)
        self.assertEqual(encoder.read_counts(), (15, 12))
        encoder.reset()
        self.assertEqual(encoder.read_counts(), (0, 0))

    def test_sensor_pode_simular_timeout(self):
        sensor = SimDistanceSensor([20.0, None, 15.5])
        self.assertEqual(sensor.read_cm(), 20.0)
        self.assertIsNone(sensor.read_cm())
        self.assertEqual(sensor.read_cm(), 15.5)

    def test_imu_simulada(self):
        imu = SimIMU(90.0)
        self.assertEqual(imu.read_yaw_deg(), 90.0)
        imu.set_invalid()
        self.assertIsNone(imu.read_yaw_deg())


if __name__ == "__main__":
    unittest.main(verbosity=2)
