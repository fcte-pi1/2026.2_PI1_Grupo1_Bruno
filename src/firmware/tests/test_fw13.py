"""Testes da FW13 - Navegação autônoma."""

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.dirname(THIS_DIR)
if FIRMWARE_DIR not in sys.path:
    sys.path.insert(0, FIRMWARE_DIR)

from navigation.map_position import MazeMap, MapPosition, EAST, WALL_FREE  # noqa: E402
from navigation.autonomous import AutonomousNavigator, STATE_GOAL, STATE_FAULT  # noqa: E402


class Reading:
    def __init__(self, distance_cm, valid=True):
        self.distance_cm = distance_cm
        self.valid = valid


class FakeSensorManager:
    def __init__(self, front=30.0, left=5.0, right=5.0, back=5.0, valid=True):
        self.values = {
            "front": Reading(front, valid),
            "left": Reading(left, valid),
            "right": Reading(right, valid),
            "back": Reading(back, valid),
        }

    def read_all(self):
        return self.values


class FixedPlanner:
    def __init__(self, direction):
        self.direction = direction

    def next_direction(self, maze, pose):
        return self.direction


class NoRoutePlanner:
    def next_direction(self, maze, pose):
        return None


class FakeMotion:
    def __init__(self, fail_forward=False):
        self.commands = []
        self.fail_forward = fail_forward

    def turn_left(self):
        self.commands.append("left")
        return True

    def turn_right(self):
        self.commands.append("right")
        return True

    def turn_around(self):
        self.commands.append("around")
        return True

    def forward_one_cell(self):
        self.commands.append("forward")
        return not self.fail_forward

    def stop(self):
        self.commands.append("stop")
        return True


class TestFW13(unittest.TestCase):
    def test_chega_ao_objetivo_e_para(self):
        maze = MazeMap(2, 1, start=(0, 0), goal=(1, 0))
        state = MapPosition(maze, initial_heading=EAST)
        sensors = FakeSensorManager(front=30.0, left=5.0, right=5.0, back=5.0)
        motion = FakeMotion()
        navigator = AutonomousNavigator(state, sensors, FixedPlanner(EAST), motion)

        result = navigator.step()

        self.assertEqual(result, STATE_GOAL)
        self.assertEqual(state.pose.as_tuple(), (1, 0))
        self.assertEqual(motion.commands, ["forward", "stop"])

    def test_sensor_frontal_invalido_causa_parada_segura(self):
        maze = MazeMap(2, 1, start=(0, 0), goal=(1, 0))
        state = MapPosition(maze, initial_heading=EAST)
        sensors = FakeSensorManager(valid=False)
        motion = FakeMotion()
        navigator = AutonomousNavigator(state, sensors, FixedPlanner(EAST), motion)

        self.assertEqual(navigator.step(), STATE_FAULT)
        self.assertEqual(navigator.fault_reason, "sensor_frontal_invalido")
        self.assertEqual(motion.commands[-1], "stop")

    def test_sem_rota_causa_parada(self):
        maze = MazeMap(2, 1, start=(0, 0), goal=(1, 0))
        state = MapPosition(maze, initial_heading=EAST)
        motion = FakeMotion()
        navigator = AutonomousNavigator(state, FakeSensorManager(), NoRoutePlanner(), motion)

        self.assertEqual(navigator.step(), STATE_FAULT)
        self.assertEqual(navigator.fault_reason, "rota_indisponivel")
        self.assertEqual(motion.commands[-1], "stop")

    def test_falha_do_movimento_nao_atualiza_posicao(self):
        maze = MazeMap(2, 1, start=(0, 0), goal=(1, 0))
        state = MapPosition(maze, initial_heading=EAST)
        motion = FakeMotion(fail_forward=True)
        navigator = AutonomousNavigator(state, FakeSensorManager(), FixedPlanner(EAST), motion)

        self.assertEqual(navigator.step(), STATE_FAULT)
        self.assertEqual(state.pose.as_tuple(), (0, 0))
        self.assertEqual(navigator.fault_reason, "falha_no_avanco")


if __name__ == "__main__":
    unittest.main(verbosity=2)
