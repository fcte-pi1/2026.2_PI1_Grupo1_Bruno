"""FW11 - Mapa e posição do Micromouse.

Compatível com Python 3 e MicroPython.
Não depende de bibliotecas externas.

Responsabilidades:
- representar células e as quatro paredes do labirinto;
- manter paredes compartilhadas coerentes entre células vizinhas;
- manter posição (x, y) e orientação do robô;
- converter direções relativas (frente/esquerda/direita/trás) em N/L/S/O;
- atualizar posição/orientação somente após movimentos confirmados.
"""

# Estados de parede
WALL_UNKNOWN = 0
WALL_FREE = 1
WALL_PRESENT = 2

# Direções absolutas. A ordem permite rotações usando módulo 4.
NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

# Direções relativas ao robô
FRONT = 0
RIGHT = 1
BACK = 2
LEFT = 3

DIRECTION_NAMES = {
    NORTH: "N",
    EAST: "L",
    SOUTH: "S",
    WEST: "O",
}

WALL_NAMES = {
    WALL_UNKNOWN: "desconhecida",
    WALL_FREE: "livre",
    WALL_PRESENT: "parede",
}

# deslocamento (dx, dy) para cada direção absoluta
_DIR_DELTA = {
    NORTH: (0, 1),
    EAST: (1, 0),
    SOUTH: (0, -1),
    WEST: (-1, 0),
}

_OPPOSITE = {
    NORTH: SOUTH,
    EAST: WEST,
    SOUTH: NORTH,
    WEST: EAST,
}


class Cell:
    """Uma célula do labirinto."""

    def __init__(self):
        self.walls = [WALL_UNKNOWN, WALL_UNKNOWN, WALL_UNKNOWN, WALL_UNKNOWN]
        self.visited = False

    def wall(self, direction):
        _validate_direction(direction)
        return self.walls[direction]

    def set_wall(self, direction, state):
        _validate_direction(direction)
        _validate_wall_state(state)
        self.walls[direction] = state


class Pose:
    """Posição e orientação atuais do Micromouse."""

    def __init__(self, x=0, y=0, heading=NORTH):
        _validate_direction(heading)
        self.x = x
        self.y = y
        self.heading = heading

    def as_tuple(self):
        return (self.x, self.y)

    def copy(self):
        return Pose(self.x, self.y, self.heading)


class MazeMap:
    """Mapa em grade com paredes conhecidas/desconhecidas."""

    def __init__(self, width, height, start=(0, 0), goal=None):
        if width <= 0 or height <= 0:
            raise ValueError("width e height devem ser positivos")

        self.width = width
        self.height = height
        self.start = start
        self.goal = goal if goal is not None else (width - 1, height - 1)

        if not self.is_valid_position(self.start[0], self.start[1]):
            raise ValueError("posição inicial fora do mapa")
        if not self.is_valid_position(self.goal[0], self.goal[1]):
            raise ValueError("objetivo fora do mapa")

        self._cells = []
        for _y in range(height):
            row = []
            for _x in range(width):
                row.append(Cell())
            self._cells.append(row)

        self._close_outer_boundaries()

    def is_valid_position(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def cell(self, x, y):
        if not self.is_valid_position(x, y):
            raise IndexError("célula fora do mapa: (%s, %s)" % (x, y))
        return self._cells[y][x]

    def mark_visited(self, x, y, visited=True):
        self.cell(x, y).visited = bool(visited)

    def is_goal(self, x, y):
        return (x, y) == self.goal

    def neighbor(self, x, y, direction):
        """Retorna (nx, ny) ou None quando a direção sai do mapa."""
        _validate_direction(direction)
        dx, dy = _DIR_DELTA[direction]
        nx = x + dx
        ny = y + dy
        if not self.is_valid_position(nx, ny):
            return None
        return (nx, ny)

    def set_wall(self, x, y, direction, state):
        """Atualiza uma parede e a face oposta da célula vizinha.

        As bordas externas nunca podem ser marcadas como livres.
        """
        _validate_direction(direction)
        _validate_wall_state(state)
        current = self.cell(x, y)
        neighbor = self.neighbor(x, y, direction)

        if neighbor is None:
            if state != WALL_PRESENT:
                raise ValueError("borda externa deve permanecer como parede")
            current.set_wall(direction, WALL_PRESENT)
            return

        current.set_wall(direction, state)
        nx, ny = neighbor
        self.cell(nx, ny).set_wall(_OPPOSITE[direction], state)

    def wall(self, x, y, direction):
        return self.cell(x, y).wall(direction)

    def can_move(self, x, y, direction, allow_unknown=False):
        """Indica se um movimento pode atravessar a face da célula.

        Por segurança, uma parede desconhecida não é considerada livre por
        padrão. O planejador pode usar allow_unknown=True quando a política de
        exploração autorizar explicitamente células desconhecidas.
        """
        state = self.wall(x, y, direction)
        if state == WALL_FREE:
            return self.neighbor(x, y, direction) is not None
        if allow_unknown and state == WALL_UNKNOWN:
            return self.neighbor(x, y, direction) is not None
        return False

    def _close_outer_boundaries(self):
        for x in range(self.width):
            self._cells[0][x].set_wall(SOUTH, WALL_PRESENT)
            self._cells[self.height - 1][x].set_wall(NORTH, WALL_PRESENT)
        for y in range(self.height):
            self._cells[y][0].set_wall(WEST, WALL_PRESENT)
            self._cells[y][self.width - 1].set_wall(EAST, WALL_PRESENT)


class MapPosition:
    """Integra mapa, pose e atualização após movimentos confirmados."""

    def __init__(self, maze, initial_heading=NORTH):
        if not isinstance(maze, MazeMap):
            raise TypeError("maze deve ser MazeMap")
        self.maze = maze
        self.pose = Pose(maze.start[0], maze.start[1], initial_heading)
        self.maze.mark_visited(self.pose.x, self.pose.y)

    def absolute_direction(self, relative_direction):
        """Converte frente/direita/trás/esquerda em direção absoluta."""
        if relative_direction not in (FRONT, RIGHT, BACK, LEFT):
            raise ValueError("direção relativa inválida")
        return (self.pose.heading + relative_direction) % 4

    def set_relative_wall(self, relative_direction, state):
        direction = self.absolute_direction(relative_direction)
        self.maze.set_wall(self.pose.x, self.pose.y, direction, state)

    def update_observation(self, front=None, left=None, right=None, back=None):
        """Atualiza as paredes observadas na célula atual.

        Cada parâmetro pode ser WALL_UNKNOWN, WALL_FREE, WALL_PRESENT ou None.
        None significa que não há nova medição para aquela direção.
        """
        observations = (
            (FRONT, front),
            (LEFT, left),
            (RIGHT, right),
            (BACK, back),
        )
        for relative_direction, state in observations:
            if state is not None:
                self.set_relative_wall(relative_direction, state)

    def confirm_turn_left(self):
        """Confirma que um giro de 90° à esquerda terminou."""
        self.pose.heading = (self.pose.heading - 1) % 4

    def confirm_turn_right(self):
        """Confirma que um giro de 90° à direita terminou."""
        self.pose.heading = (self.pose.heading + 1) % 4

    def confirm_turn_around(self):
        """Confirma que um giro de 180° terminou."""
        self.pose.heading = (self.pose.heading + 2) % 4

    def confirm_forward(self):
        """Atualiza a célula após um avanço físico confirmado.

        A função NÃO deve ser chamada antes de o módulo de movimento confirmar
        que o avanço terminou. Retorna True quando a posição foi atualizada.
        """
        direction = self.pose.heading
        neighbor = self.maze.neighbor(self.pose.x, self.pose.y, direction)
        if neighbor is None:
            return False

        # Uma parede conhecida impede atualizar a pose para uma célula inválida.
        if self.maze.wall(self.pose.x, self.pose.y, direction) == WALL_PRESENT:
            return False

        self.pose.x, self.pose.y = neighbor
        self.maze.mark_visited(self.pose.x, self.pose.y)
        return True

    def current_cell(self):
        return self.maze.cell(self.pose.x, self.pose.y)

    def goal_reached(self):
        return self.maze.is_goal(self.pose.x, self.pose.y)


def _validate_direction(direction):
    if direction not in (NORTH, EAST, SOUTH, WEST):
        raise ValueError("direção absoluta inválida")


def _validate_wall_state(state):
    if state not in (WALL_UNKNOWN, WALL_FREE, WALL_PRESENT):
        raise ValueError("estado de parede inválido")
