import unittest

from robo.controle.motores import Motores
from robo.drivers.falso import MotorFalso


class TestMotores(unittest.TestCase):
    def criar(self, **config):
        driver = MotorFalso()
        motor = Motores(driver, **config)
        return driver, motor

    def test_boot_e_habilitacao_nao_movimentam(self):
        d, m = self.criar()
        self.assertFalse(d.habilitado)
        m.enable()
        self.assertEqual(d.saidas, (0, 0))

    def test_comando_desabilitado_e_rejeitado(self):
        d, m = self.criar()
        with self.assertRaises(RuntimeError):
            m.set_output(1, 1)
        self.assertFalse(d.habilitado)

    def test_limite_rampa_e_rodas_independentes(self):
        d, m = self.criar()
        m.enable()
        m.set_output(4, -0.2)
        self.assertEqual(d.saidas, (0, 0))
        m.update(100)
        self.assertEqual(d.saidas, (0.1, -0.1))
        for _ in range(10):
            m.update(100)
        self.assertEqual(d.saidas, (0.5, -0.2))

    def test_reversao_passa_por_zero_e_aguarda_pausa(self):
        d, m = self.criar(pausa_reversao_ms=200)
        m.enable()
        m.set_output(0.2, 0)
        m.update(100)
        m.update(100)
        m.set_output(-0.2, 0)
        self.assertAlmostEqual(m.update(100)[0], 0.1)
        self.assertEqual(m.update(100)[0], 0)
        self.assertEqual(m.update(100)[0], 0)
        self.assertAlmostEqual(m.update(100)[0], -0.1)

    def test_stop_e_imediato_e_descarta_alvo(self):
        d, m = self.criar()
        m.enable()
        m.set_output(1, 1)
        m.update(100)
        m.stop()
        self.assertFalse(d.habilitado)
        self.assertEqual(d.saidas, (0, 0))
        m.enable()
        m.update(100)
        self.assertEqual(d.saidas, (0, 0))

    def test_stop_enable_nao_burla_pausa(self):
        d, m = self.criar(pausa_reversao_ms=200)
        m.enable()
        m.set_output(1, 0)
        m.update(100)
        m.stop()
        m.enable()
        m.set_output(-1, 0)
        self.assertEqual(m.update(100)[0], 0)
        self.assertLess(m.update(100)[0], 0)

    def test_deadband_nao_cria_impulso_minimo(self):
        d, m = self.criar(deadband=0.1)
        m.enable()
        m.set_output(0.09, -0.09)
        m.update(100)
        self.assertEqual(d.saidas, (0, 0))

    def test_entradas_invalidas_param(self):
        for valor in (float('nan'), float('inf'), '1', None, True):
            d, m = self.criar()
            m.enable()
            m.set_output(1, 1)
            m.update(100)
            with self.assertRaises(ValueError):
                m.set_output(0, valor)
            self.assertFalse(d.habilitado)
            self.assertEqual(d.saidas, (0, 0))

    def test_atrasos_invalidos_param(self):
        for dt in (0, -1, 101, float('nan')):
            d, m = self.criar()
            m.enable()
            with self.assertRaises(ValueError):
                m.update(dt)
            self.assertFalse(d.habilitado)

    def test_falha_de_escrita_desabilita(self):
        d, m = self.criar()
        m.enable()
        def falhar(*args):
            raise OSError('PWM indisponivel')
        d.write = falhar
        m.set_output(1, 1)
        with self.assertRaises(OSError):
            m.update(100)
        self.assertFalse(m.habilitado)
        self.assertFalse(d.habilitado)

    def test_configuracao_invalida_param(self):
        for config in ({'max_duty': 0}, {'max_duty': 2}, {'rampa_por_segundo': 0},
                       {'deadband': 0.5}, {'pausa_reversao_ms': 0}, {'max_dt_ms': -1}):
            with self.assertRaises(ValueError):
                self.criar(**config)


if __name__ == '__main__':
    unittest.main()
