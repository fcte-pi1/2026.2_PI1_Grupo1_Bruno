import unittest

from robo.aplicacao import Aplicacao


class MotorEspiao:
    def __init__(self):
        self.paradas = 0

    def stop(self):
        self.paradas += 1


class TestAplicacao(unittest.TestCase):
    def test_boot_desabilitado(self):
        motor = MotorEspiao()
        Aplicacao(motor)
        self.assertEqual(motor.paradas, 1)

    def test_saida_normal_erro_e_interrupcao_param(self):
        for erro in (None, RuntimeError, KeyboardInterrupt):
            motor = MotorEspiao()
            app = Aplicacao(motor)

            def tarefa(_):
                if erro:
                    raise erro()
                return 42

            if erro:
                with self.assertRaises(erro):
                    app.executar(tarefa)
            else:
                self.assertEqual(app.executar(tarefa), 42)
            self.assertEqual(motor.paradas, 2)


if __name__ == "__main__":
    unittest.main()
