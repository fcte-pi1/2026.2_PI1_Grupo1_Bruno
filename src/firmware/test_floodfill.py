import random
from floodfill import (Maze, Explorer, N, E, S, W, DX, DY,
                       MOVE, ARRIVED, UNREACHABLE, LIMIT)


def closed_maze(w, h):
    m = Maze(w, h)
    for i in range(w * h):
        m.walls[i] = 15
    return m


def open_wall(m, x, y, d):
    m.walls[y * m.w + x] &= ~(1 << d) & 15
    nx, ny = x + DX[d], y + DY[d]
    if 0 <= nx < m.w and 0 <= ny < m.h:
        m.walls[ny * m.w + nx] &= ~(1 << ((d + 2) & 3)) & 15


def random_maze(w, h, rng, extra_openings=0):
    #Labirinto perfeito DFS
    m = closed_maze(w, h)
    seen = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        x, y = stack[-1]
        opts = [d for d in range(4)
                if 0 <= x + DX[d] < w and 0 <= y + DY[d] < h
                and (x + DX[d], y + DY[d]) not in seen]
        if not opts:
            stack.pop()
            continue
        d = rng.choice(opts)
        open_wall(m, x, y, d)
        seen.add((x + DX[d], y + DY[d]))
        stack.append((x + DX[d], y + DY[d]))
    for _ in range(extra_openings):
        x, y, d = rng.randrange(w), rng.randrange(h), rng.randrange(4)
        if 0 <= x + DX[d] < w and 0 <= y + DY[d] < h:
            open_wall(m, x, y, d)
    return m


def run(ex, truth, path):
    #Executa validando cada movimento
    while True:
        px, py = ex.x, ex.y
        st, d = ex.step(truth.walls[py * truth.w + px])
        if st != MOVE:
            return st
        assert not truth.has_wall(px, py, d) #atravessou parede real
        path.append((ex.x, ex.y))


def explore(truth, start, goals, max_steps=None):
    ex = Explorer(Maze(truth.w, truth.h), start, goals, max_steps=max_steps)
    path = [start]
    return ex, run(ex, truth, path), path


def test_open_maze_shortest():
    ex, st, path = explore(Maze(4, 4), (0, 0), [(3, 3)])
    assert st == ARRIVED and ex.steps == 6, (st, ex.steps)


def test_dead_end_and_replan():
    t = Maze(4, 4)            # parede dupla forca desvio descoberto so ao chegar perto
    for y in range(3):
        t.set_wall(1, y, E)
    ex, st, _ = explore(t, (0, 0), [(3, 0)])
    assert st == ARRIVED and ex.replans > 1


def test_no_route():
    t = Maze(4, 4)
    t.set_wall(3, 3, W)
    t.set_wall(3, 3, S)
    ex, st, _ = explore(t, (0, 0), [(3, 3)])
    assert st == UNREACHABLE


def test_multiple_goals_picks_reachable():
    t = Maze(4, 4)
    t.set_wall(3, 3, W)
    t.set_wall(3, 3, S)
    ex, st, _ = explore(t, (0, 0), [(3, 3), (0, 3)])
    assert st == ARRIVED and (ex.x, ex.y) == (0, 3)


def test_max_steps_guard():
    ex, st, _ = explore(Maze(4, 4), (0, 0), [(3, 3)], max_steps=2)
    assert st == LIMIT


def test_return_uses_only_visited():
    rng = random.Random(7)
    truth = random_maze(4, 12, rng, extra_openings=6)
    ex, st, _ = explore(truth, (0, 0), [(3, 11)])
    assert st == ARRIVED
    known = bytearray(ex.maze.visited)      # snapshot antes do retorno
    ex.start_return()
    path = []
    st = run(ex, truth, path)
    assert st == ARRIVED and (ex.x, ex.y) == (0, 0)
    for (x, y) in path:
        assert known[y * truth.w + x] #retorno pisou em celula nao visitada


def test_random_mazes_all_sizes():
    rng = random.Random(2026)
    for (w, h) in ((4, 4), (4, 8), (4, 12), (8, 8), (16, 16)):
        for k in range(100):
            truth = random_maze(w, h, rng, extra_openings=(k % 4) * 5)
            ex, st, path = explore(truth, (0, 0), [(w - 1, h - 1)])
            assert st == ARRIVED, (w, h, k, st)
            assert ex.steps <= ex.max_steps


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok  ", name)
    print("todos os testes passaram")