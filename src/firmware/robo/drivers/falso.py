"""Saidas simuladas para testes; nao importa machine nem aciona motores."""


class MotorFalso:
    def __init__(self):
        self.habilitado = False
        self.saidas = (0.0, 0.0)
        self.historico = []

    def enable(self):
        self.habilitado = True
        self.historico.append(("enable",))

    def write(self, left, right):
        if not self.habilitado and (left or right):
            raise RuntimeError("motor desabilitado")
        self.saidas = (left, right)
        self.historico.append(("write", left, right))

    def disable(self):
        self.habilitado = False
        self.saidas = (0.0, 0.0)
        self.historico.append(("disable",))
