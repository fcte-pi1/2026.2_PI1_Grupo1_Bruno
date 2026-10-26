"""Testes de simulação da FW11 - Mapa e posição."""

import os
import sys
import unittest

# Permite executar este arquivo diretamente no PC.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.dirname(THIS_DIR)
if FIRMWARE_DIR not in sys.path:
    sys.path.insert(0, FIRMWARE_DIR)

from navigation.map_position import (  # noqa: E402
    MazeMap,
    MapPosition,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    FRONT,
    LEFT,
    RIGHT,
    WALL_UNKNOWN,
    WALL_FREE,
    WALL_PRESENT,
)


class TestFW11MapPosition(unittest.TestCase):
    def test_cria_mapa_4x4_com_bordas_fechadas(self):
        maze = MazeMap(4, 4, start=(0, 0), goal=(3, 3))

        self.assertEqual(maze.wall(0, 0, SOUTH), WALL_PRESENT)
        self.assertEqual(maze.wall(0, 0, WEST), WALL_PRESENT)
        self.assertEqual(maze.wall(3, 3, NORTH), WALL_PRESENT)
        self.assertEqual(maze.wall(3, 3, EAST), WALL_PRESENT)
        self.assertEqual(maze.wall(1, 1, NORTH), WALL_UNKNOWN)

    def test_parede_compartilhada_e_atualizada_dos_dois_lados(self):
        maze = MazeMap(4, 4)
        maze.set_wall(1, 1, EAST, WALL_PRESENT)

        self.assertEqual(maze.wall(1, 1, EAST), WALL_PRESENT)
        self.assertEqual(maze.wall(2, 1, WEST), WALL_PRESENT)

    def test_caminho_livre_compartilhado(self):
        maze = MazeMap(4, 4)
        maze.set_wall(1, 1, NORTH, WALL_FREE)

        self.assertEqual(maze.wall(1, 1, NORTH), WALL_FREE)
        self.assertEqual(maze.wall(1, 2, SOUTH), WALL_FREE)
        self.assertTrue(maze.can_move(1, 1, NORTH))

    def test_posicao_inicial_e_celula_visitada(self):
        maze = MazeMap(4, 4, start=(0, 0))
        state = MapPosition(maze, initial_heading=NORTH)

        self.assertEqual(state.pose.as_tuple(), (0, 0))
        self.assertEqual(state.pose.heading, NORTH)
        self.assertTrue(maze.cell(0, 0).visited)

    def test_orientacao_so_muda_apos_giro_confirmado(self):
        state = MapPosition(MazeMap(4, 4), initial_heading=NORTH)

        state.confirm_turn_right()
        self.assertEqual(state.pose.heading, EAST)

        state.confirm_turn_left()
        self.assertEqual(state.pose.heading, NORTH)

        state.confirm_turn_around()
        self.assertEqual(state.pose.heading, SOUTH)

    def test_avanco_confirmado_atualiza_posicao(self):
        maze = MazeMap(4, 4)
        state = MapPosition(maze, initial_heading=NORTH)

        # O sensor/percepção confirmou que a frente está livre.
        state.set_relative_wall(FRONT, WALL_FREE)

        moved = state.confirm_forward()

        self.assertTrue(moved)
        self.assertEqual(state.pose.as_tuple(), (0, 1))
        self.assertTrue(maze.cell(0, 1).visited)

    def test_avanco_nao_atualiza_posicao_quando_existe_parede(self):
        maze = MazeMap(4, 4)
        state = MapPosition(maze, initial_heading=NORTH)
        state.set_relative_wall(FRONT, WALL_PRESENT)

        moved = state.confirm_forward()

        self.assertFalse(moved)
        self.assertEqual(state.pose.as_tuple(), (0, 0))

    def test_direcoes_relativas_respeitam_orientacao(self):
        maze = MazeMap(4, 4, start=(1, 1))
        state = MapPosition(maze, initial_heading=EAST)

        state.update_observation(
            front=WALL_PRESENT,
            left=WALL_FREE,
            right=WALL_PRESENT,
        )

        # Virado para leste: frente=L, esquerda=N, direita=S.
        self.assertEqual(maze.wall(1, 1, EAST), WALL_PRESENT)
        self.assertEqual(maze.wall(1, 1, NORTH), WALL_FREE)
        self.assertEqual(maze.wall(1, 1, SOUTH), WALL_PRESENT)

    def test_objetivo(self):
        maze = MazeMap(2, 1, start=(0, 0), goal=(1, 0))
        state = MapPosition(maze, initial_heading=EAST)
        maze.set_wall(0, 0, EAST, WALL_FREE)

        self.assertFalse(state.goal_reached())
        self.assertTrue(state.confirm_forward())
        self.assertTrue(state.goal_reached())


if __name__ == "__main__":
    unittest.main(verbosity=2)
