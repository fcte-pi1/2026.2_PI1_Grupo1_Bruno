"""Testes de FW14 com fontes em microvolts; nenhum circuito é acessado."""

import unittest

from bateria import ConfiguracaoBateria, MonitorBateria


def configurar(**opcoes):
    # Divisor 3:1 e pacote fictício: valores só para testar a conversão.
    parametros = dict(r_superior_ohm=20000, r_inferior_ohm=10000,
                      adc_max_uv=3_000_000, tensao_max_v=8.4,
                      tensao_baixa_v=6.3, tensao_retomada_v=6.6)
    parametros.update(opcoes)
    return ConfiguracaoBateria(**parametros)


class FonteSimulada:
    def __init__(self, *valores):
        self.valores = iter(valores)

    def __call__(self):
        return next(self.valores)


def monitor(*valores, **config):
    return MonitorBateria(configurar(**config), FonteSimulada(*valores), "simulated")


class TestBateria(unittest.TestCase):
    def test_conversao_por_divisor(self):
        leitura = monitor(2_500_000).ler()
        self.assertAlmostEqual(leitura.tensao_v, 7.5)
        self.assertTrue(leitura.valida)
        self.assertFalse(leitura.solicitar_parada)
        self.assertEqual(leitura.estado, "normal")

    def test_calibracao_de_ganho_e_offset(self):
        leitura = monitor(2_000_000, ganho=1.05, offset_v=.1).ler()
        self.assertAlmostEqual(leitura.tensao_v, 6.4)

    def test_telemetria_compativel_sem_campos_inventados(self):
        self.assertEqual(monitor(2_500_000).ler().telemetria(),
                         dict(value=7.5, unit="V", source="simulated", valid=True))

    def test_origem_medida(self):
        leitura = MonitorBateria(configurar(), lambda: 2_500_000).ler()
        self.assertEqual(leitura.telemetria()["source"], "measured")

    def test_sem_sensor(self):
        leitura = MonitorBateria(configurar()).ler()
        self.assertIsNone(leitura.tensao_v)
        self.assertFalse(leitura.valida)
        self.assertTrue(leitura.solicitar_parada)
        self.assertEqual(leitura.estado, "indisponivel")

    def test_sem_configuracao_nao_acessa_sensor(self):
        def proibido():
            raise AssertionError("nao deve ler sem configuracao")
        self.assertEqual(MonitorBateria(ler_uv=proibido).ler().estado, "indisponivel")

    def test_ausencia_explicita_nao_vira_zero(self):
        leitura = monitor(None).ler()
        self.assertEqual(leitura.telemetria(),
                         dict(value=None, unit="V", source="simulated", valid=False))
        self.assertTrue(leitura.solicitar_parada)

    def test_leituras_adc_incoerentes(self):
        for uv in (-1, 0, 3_000_000, 3_000_001, float('nan'),
                   float('inf'), float('-inf'), True, '2500000'):
            with self.subTest(uv=uv):
                leitura = monitor(uv).ler()
                self.assertEqual(leitura.estado, "incoerente")
                self.assertIsNone(leitura.tensao_v)
                self.assertTrue(leitura.solicitar_parada)

    def test_tensao_acima_do_pacote(self):
        leitura = monitor(2_900_000).ler()  # 8,7 V, ainda abaixo do teto do ADC.
        self.assertEqual(leitura.estado, "incoerente")
        self.assertFalse(leitura.valida)

    def test_limite_maximo_do_pacote_e_valido(self):
        leitura = monitor(2_800_000).ler()
        self.assertAlmostEqual(leitura.tensao_v, 8.4)
        self.assertTrue(leitura.valida)

    def test_offset_nao_pode_produzir_tensao_negativa(self):
        self.assertEqual(monitor(100, offset_v=-.1).ler().estado, "incoerente")

    def test_baixa_tensao_e_medida_valida_que_solicita_parada(self):
        leitura = monitor(2_000_000).ler()
        self.assertAlmostEqual(leitura.tensao_v, 6)
        self.assertTrue(leitura.valida)
        self.assertTrue(leitura.solicitar_parada)
        self.assertEqual(leitura.estado, "baixa")

    def test_histerese_evita_oscilacao(self):
        m = monitor(2_500_000, 2_000_000, 2_150_000, 2_200_000)
        self.assertEqual([m.ler().estado for _ in range(4)],
                         ["normal", "baixa", "baixa", "normal"])

    def test_falha_nao_apaga_bloqueio_de_baixa(self):
        m = monitor(2_000_000, None, 2_150_000, 2_250_000)
        self.assertEqual([m.ler().estado for _ in range(4)],
                         ["baixa", "indisponivel", "baixa", "normal"])

    def test_baixa_inclui_o_limiar(self):
        self.assertEqual(monitor(2_100_000).ler().estado, "baixa")

    def test_erro_de_aquisicao(self):
        def falha():
            raise OSError("ADC indisponivel")
        leitura = MonitorBateria(configurar(), falha).ler()
        self.assertEqual(leitura.estado, "erro_sensor")
        self.assertFalse(leitura.valida)
        self.assertTrue(leitura.solicitar_parada)

    def test_erro_de_programacao_nao_e_ocultado(self):
        def falha():
            raise TypeError("adaptador incorreto")
        with self.assertRaises(TypeError):
            MonitorBateria(configurar(), falha).ler()

    def test_rejeita_configuracao_fisica_invalida(self):
        for campo in ("r_superior_ohm", "r_inferior_ohm", "adc_max_uv",
                      "tensao_max_v", "tensao_baixa_v", "tensao_retomada_v", "ganho"):
            for valor in (0, -1, float('nan'), float('inf'), True):
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    configurar(**{campo: valor})
        with self.assertRaises(ValueError):
            configurar(offset_v=float('nan'))

    def test_rejeita_limiares_invertidos(self):
        for opcoes in (dict(tensao_retomada_v=6.3), dict(tensao_retomada_v=6.2),
                       dict(tensao_retomada_v=9)):
            with self.subTest(opcoes=opcoes), self.assertRaises(ValueError):
                configurar(**opcoes)

    def test_rejeita_divisor_sem_margem_adc(self):
        with self.assertRaises(ValueError):
            configurar(r_superior_ohm=10000)
        with self.assertRaises(ValueError):
            configurar(tensao_max_v=9)

    def test_rejeita_origem_e_adaptador_invalidos(self):
        for opcoes in (dict(origem="estimated"), dict(ler_uv=123), dict(configuracao={})):
            with self.subTest(opcoes=opcoes), self.assertRaises(ValueError):
                MonitorBateria(**opcoes)


if __name__ == '__main__':
    unittest.main()
