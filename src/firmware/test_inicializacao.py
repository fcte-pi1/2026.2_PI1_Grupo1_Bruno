import unittest

import config_exemplo
from robo.inicializacao import criar
from test_ponte_pwm import MachineFake, config_fake


class TestInicializacao(unittest.TestCase):
    def test_config_exemplo_bloqueia_hardware(self):
        fake = MachineFake()
        with self.assertRaises(ValueError):
            criar(config_exemplo, fake)
        self.assertEqual(fake.eventos, [])

    def test_config_confirmada_inicia_desabilitada(self):
        class Config:
            HARDWARE = config_fake()
            CONTROLE = config_exemplo.CONTROLE
        fake = MachineFake()
        app = criar(Config, fake)
        self.assertFalse(app.motores.habilitado)
        self.assertEqual(fake.pinos[0].valor, 0)
        self.assertEqual(fake.pwms[3].duty, 0)
        self.assertEqual(fake.pwms[6].duty, 0)

    def test_config_controle_invalida_desabilita(self):
        class Config:
            HARDWARE = config_fake()
            CONTROLE = {'max_duty': 10}
        fake = MachineFake()
        with self.assertRaises(ValueError):
            criar(Config, fake)
        self.assertEqual(fake.pinos[0].valor, 0)


if __name__ == '__main__':
    unittest.main()
