"""Executavel em CPython/MicroPython, sem unittest e SEM acesso ao hardware."""

import sys
import robo.navegacao
import robo.protocolo
from config_exemplo import CONTROLE
from robo.aplicacao import Aplicacao
from robo.controle.motores import Motores
from robo.drivers.falso import MotorFalso


def executar():
    driver = MotorFalso()
    motores = Motores(driver, **CONTROLE)
    app = Aplicacao(motores)
    assert not driver.habilitado
    assert driver.saidas == (0, 0)

    def tarefa(m):
        m.enable()
        m.set_output(0.2, -0.2)
        m.update(100)
        assert driver.saidas == (0.1, -0.1)
        m.update(100)
        assert driver.saidas == (0.2, -0.2)

    app.executar(tarefa)
    assert not driver.habilitado
    assert driver.saidas == (0, 0)
    print('SMOKE OK - runtime:', sys.implementation.name, sys.version)
    print('Origem: simulada. Nenhum GPIO ou motor fisico foi acionado.')


if __name__ == '__main__':
    executar()
