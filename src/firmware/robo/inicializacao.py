"""Composicao da aplicacao: hardware so mediante configuracao externa."""

from robo.aplicacao import Aplicacao
from robo.controle.motores import Motores

_app = None


def criar(config, machine_module=None):
    from robo.drivers.ponte_pwm import PontePWM
    driver = PontePWM(config.HARDWARE, machine_module)
    try:
        return Aplicacao(Motores(driver, **config.CONTROLE))
    except BaseException:
        driver.disable()
        raise


def iniciar():
    global _app
    if _app is None:
        # TODO(INT02/#22): criar config_local somente apos confirmar hardware.
        # Nao ha fallback silencioso para fake ou pinagem de outro projeto.
        import config_local
        _app = criar(config_local)
    return _app
