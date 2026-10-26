import math
import unittest

from odometria import EncoderQuadratura, Odometria


def criar(**opcoes):
    # Circunferência de 100 mm / 100 contagens: 1 mm por contagem.
    config = dict(diametro_esquerdo_mm=100 / math.pi,
                  diametro_direito_mm=100 / math.pi,
                  contagens_por_volta_esquerda=100,
                  contagens_por_volta_direita=100, distancia_rodas_mm=100)
    config.update(opcoes)
    return Odometria(**config)


class TestOdometria(unittest.TestCase):
    def test_primeira_amostra_nao_inventa_velocidade(self):
        o = criar()
        self.assertIsNone(o.atualizar(150, 200, 500))
        self.assertEqual(o.x_mm, 0)

    def test_avanco_e_re_com_tempo_real(self):
        for sinal in (1, -1):
            with self.subTest(sinal=sinal):
                o = criar()
                o.atualizar(0, 0, 0)
                a = o.atualizar(sinal * 100, sinal * 100, 500)
                self.assertAlmostEqual(a.velocidade_esquerda, sinal * 200)
                self.assertAlmostEqual(a.velocidade_direita, sinal * 200)
                self.assertAlmostEqual(a.x_mm, sinal * 100)
                self.assertAlmostEqual(a.y_mm, 0)
                self.assertAlmostEqual(a.theta_rad, 0)

    def test_roda_parada_descreve_arco(self):
        o = criar()
        o.atualizar(0, 0, 0)
        a = o.atualizar(0, 100, 1000)
        self.assertEqual(a.velocidade_esquerda, 0)
        self.assertAlmostEqual(a.velocidade_direita, 100)
        self.assertAlmostEqual(a.theta_rad, 1)
        self.assertAlmostEqual(a.x_mm, 50 * math.sin(1))
        self.assertAlmostEqual(a.y_mm, 50 * (1 - math.cos(1)))

    def test_curva_com_duas_rodas_em_movimento(self):
        o = criar()
        o.atualizar(0, 0, 0)
        a = o.atualizar(50, 100, 1000)
        self.assertAlmostEqual(a.theta_rad, .5)
        self.assertAlmostEqual(a.x_mm, 150 * math.sin(.5))
        self.assertAlmostEqual(a.y_mm, 150 * (1 - math.cos(.5)))

    def test_giro_no_proprio_eixo(self):
        o = criar()
        o.atualizar(0, 0, 0)
        a = o.atualizar(-50, 50, 1000)
        self.assertAlmostEqual(a.theta_rad, 1)
        self.assertAlmostEqual(a.x_mm, 0)
        self.assertAlmostEqual(a.y_mm, 0)

    def test_parado(self):
        o = criar()
        o.atualizar(10, 20, 0)
        a = o.atualizar(10, 20, 30)
        self.assertEqual(a.velocidade_esquerda, 0)
        self.assertEqual(a.velocidade_direita, 0)

    def test_polaridade_e_geometria_independentes(self):
        o = criar(polaridade_esquerda=-1, diametro_direito_mm=200 / math.pi)
        o.atualizar(0, 0, 0)
        a = o.atualizar(-100, 50, 1000)
        self.assertAlmostEqual(a.x_mm, 100)
        self.assertAlmostEqual(a.theta_rad, 0)

    def test_overflow_nos_dois_sentidos(self):
        for antes, depois, esperado in ((250, 4, 10), (4, 250, -10)):
            with self.subTest(antes=antes):
                o = criar(modulo_contador=256)
                o.atualizar(antes, antes, 0)
                a = o.atualizar(depois, depois, 1000)
                self.assertAlmostEqual(a.x_mm, esperado)

    def test_ticks_diff_com_wrap(self):
        diferenca = lambda a, b: (a - b + 512) % 1024 - 512
        o = criar(diferenca_tempo=diferenca)
        o.atualizar(0, 0, 1000)
        a = o.atualizar(10, 10, 26)
        self.assertEqual(a.dt_ms, 50)
        self.assertAlmostEqual(a.velocidade_esquerda, 200)

    def test_reset_explicito_preserva_pose(self):
        o = criar()
        o.atualizar(0, 0, 0)
        o.atualizar(100, 100, 1000)
        o.rebasear(0, 0, 0)
        a = o.atualizar(10, 10, 100)
        self.assertAlmostEqual(a.x_mm, 110)
        self.assertAlmostEqual(o.distancia_esquerda_mm, 110)
        self.assertAlmostEqual(a.velocidade_esquerda, 100)

    def test_rejeita_tempo_invalido_sem_consumir_contagens(self):
        o = criar()
        o.atualizar(0, 0, 100)
        for tempo in (100, 99):
            with self.assertRaises(ValueError):
                o.atualizar(10, 10, tempo)
        self.assertAlmostEqual(o.atualizar(20, 20, 200).x_mm, 20)

    def test_rejeita_delta_ambiguo_sem_mudar_pose(self):
        o = criar(modulo_contador=256)
        o.atualizar(0, 0, 0)
        with self.assertRaises(ValueError):
            o.atualizar(10, 128, 100)
        self.assertEqual(o.x_mm, 0)
        self.assertAlmostEqual(o.atualizar(10, 10, 100).x_mm, 10)

    def test_rejeita_configuracao_invalida(self):
        for valor in (0, -1, float('inf'), float('nan')):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                criar(diametro_esquerdo_mm=valor)
        for modulo in (0, 3, 255, 256.5, True):
            with self.subTest(modulo=modulo), self.assertRaises(ValueError):
                criar(modulo_contador=modulo)
        with self.assertRaises(ValueError):
            criar(polaridade_direita=0)

    def test_rejeita_contagem_fracionaria(self):
        with self.assertRaises(ValueError):
            criar().atualizar(.5, 0, 0)

    def test_volta_completa_nao_desloca_centro(self):
        o = criar()
        o.atualizar(0, 0, 0)
        # 628 passos de giro e avanço: o arco composto deve fechar.
        for i in range(1, 629):
            o.atualizar(i, 2 * i, i * 10)
        self.assertAlmostEqual(o.x_mm, 150 * math.sin(6.28), places=7)
        self.assertAlmostEqual(o.y_mm, 150 * (1 - math.cos(6.28)), places=7)
        self.assertTrue(-math.pi <= o.theta_rad < math.pi)


class TestQuadratura(unittest.TestCase):
    def test_quatro_bordas_por_ciclo_e_reversao(self):
        e = EncoderQuadratura()
        for a, b in ((0, 1), (1, 1), (1, 0), (0, 0)):
            e.atualizar(a, b)
        self.assertEqual(e.read(), 4)
        for a, b in ((1, 0), (1, 1), (0, 1), (0, 0)):
            e.atualizar(a, b)
        self.assertEqual(e.read(), 0)

    def test_sinal_estavel_nao_conta(self):
        e = EncoderQuadratura(1, 0)
        for _ in range(10):
            e.atualizar(1, 0)
        self.assertEqual(e.read(), 0)

    def test_transicao_invalida_ressincroniza(self):
        e = EncoderQuadratura()
        e.atualizar(1, 1)
        self.assertEqual(e.transicoes_invalidas, 1)
        self.assertEqual(e.read(), 0)
        self.assertEqual(e.atualizar(1, 0), 1)

    def test_pulsos_simulados_alimentam_odometria(self):
        esq, dire = EncoderQuadratura(), EncoderQuadratura()
        o = criar()
        o.atualizar(esq.read(), dire.read(), 0)
        for _ in range(25):
            for a, b in ((0, 1), (1, 1), (1, 0), (0, 0)):
                esq.atualizar(a, b)
                dire.atualizar(a, b)
        a = o.atualizar(esq.read(), dire.read(), 500)
        self.assertAlmostEqual(a.x_mm, 100)
        self.assertAlmostEqual(a.velocidade_esquerda, 200)


if __name__ == '__main__':
    unittest.main()
