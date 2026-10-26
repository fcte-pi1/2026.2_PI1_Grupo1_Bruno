import unittest

from robo.drivers.ponte_pwm import PontePWM


def config_fake():
    # Numeros e tabela sinteticos: NAO SAO pinagem de ESP32 nem driver real.
    return dict(confirmado=True, placa='fake', driver='fake', fonte_tabela='teste',
                comportamento_desabilitado='simulado', interface='2in_pwm_enable',
                enable_gpio=0, enable_ativo=1, esquerda=(1, 2, 3), direita=(4, 5, 6),
                gpios_saida_aprovados=list(range(7)), pwm_hz=1000,
                tabela={'frente': (1, 0), 're': (0, 1), 'zero': (0, 0)})


class MachineFake:
    def __init__(self):
        self.eventos = []
        self.pinos = {}
        self.pwms = {}
        fake = self

        class Pin:
            OUT = 1

            def __init__(self, gpio, mode, value):
                self.gpio = gpio
                fake.pinos[gpio] = self
                self.value(value)

            def value(self, valor):
                self.valor = valor
                fake.eventos.append(('pin', self.gpio, valor))

        class PWM:
            def __init__(self, pin, freq, duty_u16):
                self.gpio = pin.gpio
                self.freq = freq
                fake.pwms[self.gpio] = self
                self.duty_u16(duty_u16)

            def duty_u16(self, valor):
                self.duty = valor
                fake.eventos.append(('pwm', self.gpio, valor))

            def deinit(self):
                self.duty_u16(0)

        self.Pin = Pin
        self.PWM = PWM


class TestPonte(unittest.TestCase):
    def test_config_ausente_nao_importa_machine(self):
        with self.assertRaises(ValueError):
            PontePWM(None)

    def test_config_invalida_nao_toca_gpio_param(self):
        for alteracao in ({'confirmado': False}, {'esquerda': (0, 2, 3)},
                          {'enable_ativo': 2}, {'gpios_saida_aprovados': []},
                          {'pwm_hz': 0}, {'interface': 'desconhecida'}):
            fake = MachineFake()
            config = config_fake()
            config.update(alteracao)
            with self.assertRaises(ValueError):
                PontePWM(config, fake)
            self.assertEqual(fake.eventos, [])

    def test_primeiro_sinal_desabilita_enable_param(self):
        for ativo in (0, 1):
            fake = MachineFake()
            config = config_fake()
            config['enable_ativo'] = ativo
            ponte = PontePWM(config, fake)
            self.assertEqual(fake.eventos[0], ('pin', 0, 1 - ativo))
            self.assertFalse(ponte.habilitado)
            self.assertEqual(fake.pwms[3].duty, 0)
            self.assertEqual(fake.pwms[6].duty, 0)

    def test_pwm_sentido_e_ordem_dos_sinais(self):
        fake = MachineFake()
        ponte = PontePWM(config_fake(), fake)
        ponte.enable()
        fake.eventos.clear()
        ponte.write(0.5, -0.25)
        self.assertEqual(fake.eventos, [
            ('pwm', 3, 0), ('pin', 1, 1), ('pin', 2, 0), ('pwm', 3, 32768),
            ('pwm', 6, 0), ('pin', 4, 0), ('pin', 5, 1), ('pwm', 6, 16384)])
        ponte.disable()
        self.assertEqual(fake.pinos[0].valor, 0)
        self.assertEqual(fake.pwms[3].duty, 0)
        self.assertEqual(fake.pwms[6].duty, 0)

    def test_duty_invalido_para_ambos(self):
        fake = MachineFake()
        ponte = PontePWM(config_fake(), fake)
        ponte.enable()
        ponte.write(0.5, 0.5)
        with self.assertRaises(ValueError):
            ponte.write(0, float('nan'))
        self.assertFalse(ponte.habilitado)
        self.assertEqual(fake.pwms[3].duty, 0)

    def test_falha_em_pwm_ainda_desabilita_outro_motor(self):
        fake = MachineFake()
        ponte = PontePWM(config_fake(), fake)
        ponte.enable()
        ponte.write(0.5, 0.5)
        def falhar(_):
            raise OSError('falha PWM esquerdo')
        fake.pwms[3].duty_u16 = falhar
        with self.assertRaises(OSError):
            ponte.disable()
        self.assertEqual(fake.pinos[0].valor, 0)
        self.assertEqual(fake.pwms[6].duty, 0)


if __name__ == '__main__':
    unittest.main()
