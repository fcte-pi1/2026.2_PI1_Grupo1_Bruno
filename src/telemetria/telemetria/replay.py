from bisect import bisect_right
from copy import deepcopy

from telemetria.mapa import EstadoMapa
from telemetria.modelos import Frame

VELOCIDADES = (0.5, 1.0, 2.0, 4.0)


class Replay:
    """Reconstrói o mapa de uma execução salva; guarda cópias periódicas para pular na linha do tempo."""

    def __init__(self, frames: list[Frame], intervalo_copia: int = 50) -> None:
        if intervalo_copia < 1:
            raise ValueError("intervalo_copia deve ser positivo")
        self.frames = sorted(frames, key=lambda f: (f.boot_id, f.seq))
        self.tempos = [f.t_ms for f in self.frames]
        self._copias: list[EstadoMapa] = []
        self._intervalo = intervalo_copia
        estado = EstadoMapa()
        for indice, frame in enumerate(self.frames):
            if indice % intervalo_copia == 0:
                self._copias.append(deepcopy(estado))
            estado.aplicar(frame)
        self.final = estado

    @property
    def total(self) -> int:
        return len(self.frames)

    @property
    def inicio_ms(self) -> int:
        return self.tempos[0] if self.tempos else 0

    @property
    def fim_ms(self) -> int:
        return self.tempos[-1] if self.tempos else 0

    def estado(self, aplicados: int) -> EstadoMapa:
        """Estado depois de aplicar os primeiros `aplicados` frames."""
        aplicados = max(0, min(aplicados, self.total))
        if aplicados == self.total:
            return self.final
        base = aplicados // self._intervalo
        estado = deepcopy(self._copias[base])
        for frame in self.frames[base * self._intervalo : aplicados]:
            estado.aplicar(frame)
        return estado

    def aplicados_ate(self, t_ms: int) -> int:
        return bisect_right(self.tempos, t_ms)
