"""FW13 - Integração da navegação autônoma.

Este módulo NÃO implementa Flood Fill nem controle físico de motores. Ele liga
percepção, FW11 (mapa/posição), planejador e movimentos por interfaces, para
não duplicar o trabalho das outras issues.
"""

from navigation.map_position import (
    NORTH,
    EAST,
    SOUTH,
    WEST,
    FRONT,
    RIGHT,
    BACK,
    LEFT,
    WALL_FREE,
    WALL_PRESENT,
)

STATE_READY = "ready"
STATE_RUNNING = "running"
STATE_GOAL = "goal"
STATE_FAULT = "fault"


class AutonomousNavigator:
    def __init__(self, map_position, sensor_manager, planner, motion, wall_threshold_cm=12.0):
        self.map_position = map_position
        self.sensor_manager = sensor_manager
        self.planner = planner
        self.motion = motion
        self.wall_threshold_cm = float(wall_threshold_cm)
        self.state = STATE_READY
        self.fault_reason = None

    def _distance_to_wall_state(self, reading):
        if reading is None or not reading.valid:
            return None
        if reading.distance_cm <= self.wall_threshold_cm:
            return WALL_PRESENT
        return WALL_FREE

    def perceive(self):
        readings = self.sensor_manager.read_all()
        front = self._distance_to_wall_state(readings.get("front"))
        left = self._distance_to_wall_state(readings.get("left"))
        right = self._distance_to_wall_state(readings.get("right"))
        back = self._distance_to_wall_state(readings.get("back"))

        # Para a navegação segura desta integração, a leitura frontal é tratada
        # como indispensável. As demais só atualizam o mapa quando válidas.
        if front is None:
            return False

        self.map_position.update_observation(front=front, left=left, right=right, back=back)
        return True

    def _turn_to(self, desired_heading):
        current = self.map_position.pose.heading
        delta = (desired_heading - current) % 4

        if delta == 0:
            return True
        if delta == 1:
            if not self.motion.turn_right():
                return False
            self.map_position.confirm_turn_right()
            return True
        if delta == 3:
            if not self.motion.turn_left():
                return False
            self.map_position.confirm_turn_left()
            return True
        if delta == 2:
            if not self.motion.turn_around():
                return False
            self.map_position.confirm_turn_around()
            return True
        return False

    def fail(self, reason):
        self.state = STATE_FAULT
        self.fault_reason = reason
        self.motion.stop()
        return False

    def start(self):
        if self.map_position.goal_reached():
            self.motion.stop()
            self.state = STATE_GOAL
            return True
        self.state = STATE_RUNNING
        return True

    def step(self):
        """Executa um ciclo percepção -> planejamento -> movimento."""
        if self.state == STATE_READY:
            self.start()
        if self.state in (STATE_GOAL, STATE_FAULT):
            return self.state

        if not self.perceive():
            self.fail("sensor_frontal_invalido")
            return self.state

        desired_heading = self.planner.next_direction(
            self.map_position.maze,
            self.map_position.pose,
        )
        if desired_heading not in (NORTH, EAST, SOUTH, WEST):
            self.fail("rota_indisponivel")
            return self.state

        if not self._turn_to(desired_heading):
            self.fail("falha_no_giro")
            return self.state

        # Depois do giro, a parede absoluta na frente deve ser livre. Se o
        # planejador escolheu uma direção ainda desconhecida, o ciclo seguinte
        # de percepção deverá confirmá-la antes do avanço físico.
        current = self.map_position.pose
        wall = self.map_position.maze.wall(current.x, current.y, current.heading)
        if wall == WALL_PRESENT:
            self.fail("movimento_bloqueado_por_parede")
            return self.state

        if not self.motion.forward_one_cell():
            self.fail("falha_no_avanco")
            return self.state

        if not self.map_position.confirm_forward():
            self.fail("posicao_nao_confirmada")
            return self.state

        if self.map_position.goal_reached():
            self.motion.stop()
            self.state = STATE_GOAL

        return self.state
