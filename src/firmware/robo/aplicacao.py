"""Ciclo de vida independente da placa e sem partida automatica."""


class Aplicacao:
    def __init__(self, motores):
        self.motores = motores
        self.motores.stop()

    def executar(self, tarefa):
        """Sempre desabilita saidas ao terminar, falhar ou receber Ctrl-C."""
        try:
            return tarefa(self.motores)
        finally:
            self.motores.stop()
