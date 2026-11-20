"""Decisoes puras: sem GPIO, rede, relogio ou efeitos em motores."""
DELTA = ((0, 1), (1, 0), (0, -1), (-1, 0))
RELATIVE = ('front', 'right', 'back', 'left')


def patrol_choice(scan, stop_mm, turn_clearance):
    """Prioriza seguir reto. Patrulha reativa NAO garante resolver labirintos."""
    if any(scan.get(k) is None for k in RELATIVE):
        return 'FAULT'
    if scan['front'] > stop_mm:
        return 'FORWARD'
    if min(scan.values()) <= turn_clearance:
        return 'BLOCKED'
    if scan['right'] > stop_mm:
        return 'RIGHT'
    if scan['left'] > stop_mm:
        return 'LEFT'
    if scan['back'] > stop_mm:
        return 'BACK'
    return 'BLOCKED'


def classify(scan, wall_mm, hysteresis):
    """Faixa ambigua/timeout nao e abertura. Exige nova medicao parado."""
    result = []
    for name in RELATIVE:
        d = scan.get(name)
        if d is None or abs(d - wall_mm) <= hysteresis:
            raise ValueError('Parede indefinida: ' + name)
        result.append(d > wall_mm)
    return result


class Explorer:
    """DFS em grade relativa, aceita qualquer celula inicial como (0,0).

    Requer inicio centrado/alinhado e passos de uma celula calibrados. A pose
    so muda em commit, apos o controlador confirmar giro e translacao.
    """
    def __init__(self, max_cells=256, goal=None):
        self.pos = (0, 0)
        self.heading = 0
        self.visited = {self.pos}
        self.stack = [self.pos]
        self.pending = None
        self.max_cells = max_cells
        self.goal = goal

    def choose(self, openings):
        if self.pending is not None:
            raise ValueError('Movimento anterior ainda nao confirmado.')
        if len(openings) != 4 or any(type(v) is not bool for v in openings):
            raise ValueError('Quatro observacoes booleanas obrigatorias.')
        if self.goal is not None and self.pos == self.goal:
            return 'GOAL', None
        for relative in (1, 0, 3, 2):
            heading = (self.heading + relative) % 4
            dx, dy = DELTA[heading]
            target = (self.pos[0] + dx, self.pos[1] + dy)
            if openings[relative] and target not in self.visited:
                if len(self.visited) >= self.max_cells:
                    return 'LIMIT', None
                self.pending = (target, heading, False)
                return 'MOVE', relative
        if len(self.stack) == 1:
            return 'EXPLORED', None
        parent = self.stack[-2]
        for direction, (dx, dy) in enumerate(DELTA):
            if (self.pos[0] + dx, self.pos[1] + dy) == parent:
                relative = (direction - self.heading) % 4
                if not openings[relative]:
                    return 'BLOCKED', None
                self.pending = (parent, direction, True)
                return 'MOVE', relative
        raise ValueError('Caminho de retorno inconsistente.')

    def commit(self):
        if self.pending is None:
            raise ValueError('Nenhum movimento pendente.')
        target, heading, returning = self.pending
        self.pos, self.heading = target, heading
        if returning:
            self.stack.pop()
        else:
            self.visited.add(target)
            self.stack.append(target)
        self.pending = None

    def abort(self):
        self.pending = None
