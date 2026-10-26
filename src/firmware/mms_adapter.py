"""Adaptador OPCIONAL para o simulador mms (github.com/mackorone/mms).

Fica fora do nucleo: floodfill.py nao importa nada daqui.
No mms, configure o comando de execucao como `python3 mms_adapter.py`
com o diretorio de trabalho na pasta deste arquivo.
Origem do mms = canto inferior esquerdo, robo comeca virado para o norte.
"""
import sys
import API  # fornecido pelo mms
from floodfill import Maze, Explorer, N, MOVE, ARRIVED

LETTERS = "nesw"


def log(msg):
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()


def sensed_walls(heading):
    """Converte frente/direita/esquerda em mascara de paredes absolutas."""
    mask = 0
    if API.wallFront():
        mask |= 1 << heading
    if API.wallRight():
        mask |= 1 << ((heading + 1) & 3)
    if API.wallLeft():
        mask |= 1 << ((heading + 3) & 3)
    return mask


def turn_to(heading, target):
    diff = (target - heading) & 3
    if diff == 1:
        API.turnRight()
    elif diff == 2:
        API.turnRight()
        API.turnRight()
    elif diff == 3:
        API.turnLeft()
    return target


def run_phase(ex, heading):
    while True:
        x, y = ex.x, ex.y
        mask = sensed_walls(heading)
        status, d = ex.step(mask)
        for k in range(4):
            if (mask >> k) & 1:
                API.setWall(x, y, LETTERS[k])
        dist = ex.maze.dist[y * ex.maze.w + x]
        API.setText(x, y, str(dist) if dist != 0xFFFF else "-")
        if status != MOVE:
            return status, heading
        heading = turn_to(heading, d)
        API.moveForward()


def main():
    w, h = API.mazeWidth(), API.mazeHeight()
    if w == 16 and h == 16:
        goals = [(7, 7), (7, 8), (8, 7), (8, 8)]  # centro: testa objetivo multiplo
    else:
        goals = [(w - 1, h - 1)]  # canto oposto (D4, D8 ou D12 nos labirintos 4xN)
    ex = Explorer(Maze(w, h), (0, 0), goals, heading=N)
    status, heading = run_phase(ex, N)
    log("ida: status=%d passos=%d replans=%d" % (status, ex.steps, ex.replans))
    if status == ARRIVED:
        ex.start_return()
        status, heading = run_phase(ex, heading)
        log("volta: status=%d passos=%d" % (status, ex.steps))


if __name__ == "__main__":
    main()