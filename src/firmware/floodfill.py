from array import array

N, E, S, W = 0, 1, 2, 3
DX = (0, 1, 0, -1)
DY = (1, 0, -1, 0)
INF = 0xFFFF

MOVE, ARRIVED, UNREACHABLE, LIMIT = 0, 1, 2, 3


class Maze:
    """Mapa descoberto: paredes conhecidas, celulas visitadas e distancias."""
    #Descobre o mapa
    def __init__(self, w, h):
        self.w = w
        self.h = h
        n = w * h
        self.walls = bytearray(n)
        self.visited = bytearray(n)
        self.dist = array('H', [INF] * n)
        self._q = array('H', [0] * n)  # fila de tamanho fixo (cada celula entra 1x)
        for x in range(w):
            self.walls[x] |= 1 << S
            self.walls[(h - 1) * w + x] |= 1 << N
        for y in range(h):
            self.walls[y * w] |= 1 << W
            self.walls[y * w + w - 1] |= 1 << E

    def has_wall(self, x, y, d):
        return (self.walls[y * self.w + x] >> d) & 1 == 1

    def set_wall(self, x, y, d):
        #Registra paredes dos lados
        i = y * self.w + x
        new = not ((self.walls[i] >> d) & 1)
        self.walls[i] |= 1 << d
        nx = x + DX[d]
        ny = y + DY[d]
        if 0 <= nx < self.w and 0 <= ny < self.h:
            self.walls[ny * self.w + nx] |= 1 << ((d + 2) & 3)
        return new

    def observe(self, x, y, mask):
        #Marca a celula como visitada, e registra paredes lidas

        self.visited[y * self.w + x] = 1
        changed = False
        for d in range(4):
            if (mask >> d) & 1 and self.set_wall(x, y, d):
                changed = True
        return changed

    def flood(self, targets, only_visited=False):
        #BFS
        w = self.w
        dist = self.dist
        q = self._q
        walls = self.walls
        vis = self.visited
        for i in range(w * self.h):
            dist[i] = INF
        head = 0
        tail = 0
        for t in targets:
            i = t[1] * w + t[0]
            if dist[i] == INF:
                dist[i] = 0
                q[tail] = i
                tail += 1
        while head < tail:
            i = q[head]
            head += 1
            x = i % w
            y = i // w
            nd = dist[i] + 1
            for d in range(4):
                if (walls[i] >> d) & 1:
                    continue
                j = (y + DY[d]) * w + (x + DX[d])
                if dist[j] != INF:
                    continue
                if only_visited and not vis[j]:
                    continue
                dist[j] = nd
                q[tail] = j
                tail += 1

    def best_dir(self, x, y, prefer):
        #Direcao que reduz a distancia em 1, prefere seguir reto, e retorna -1 se não tem
        i = y * self.w + x
        cur = self.dist[i]
        for d in (prefer, (prefer + 1) & 3, (prefer + 3) & 3, (prefer + 2) & 3):
            if (self.walls[i] >> d) & 1:
                continue
            if self.dist[(y + DY[d]) * self.w + (x + DX[d])] == cur - 1:
                return d
        return -1


class Explorer:

    def __init__(self, maze, start, goals, heading=N, max_steps=None):
        self.maze = maze
        self.start = start
        self.goals = goals           
        self.targets = goals
        self.only_visited = False
        self.x, self.y = start
        self.heading = heading
        self.steps = 0
        self.replans = 0
        n = maze.w * maze.h
        # Guarda anti-loop: sem ela, ruido de sensor poderia girar para sempre.
        self.max_steps = max_steps if max_steps is not None else 2 * n * n
        self._dirty = True

    def set_position(self, x, y, heading):
        self.x, self.y, self.heading = x, y, heading

    def start_return(self):
        self.targets = [self.start]
        self.only_visited = True
        self._dirty = True

    def step(self, walls_mask):
        m = self.maze
        if m.observe(self.x, self.y, walls_mask):
            self._dirty = True
        if self._dirty:
            m.flood(self.targets, self.only_visited)
            self.replans += 1
            self._dirty = False
        cur = m.dist[self.y * m.w + self.x]
        if cur == 0:
            return ARRIVED, -1
        if cur == INF:
            return UNREACHABLE, -1      
        if self.steps >= self.max_steps:
            return LIMIT, -1
        d = m.best_dir(self.x, self.y, self.heading)
        if d < 0:
            return UNREACHABLE, -1
        self.x += DX[d]
        self.y += DY[d]
        self.heading = d
        self.steps += 1
        return MOVE, d