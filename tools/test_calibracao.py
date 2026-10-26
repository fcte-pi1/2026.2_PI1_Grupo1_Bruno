import contextlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

from calibracao import (CAMPOS_MOVIMENTO, analisar_autonomia, analisar_movimentos,
                        diametro_por_volta, distancia_rodas_corrigida, ler_csv, main)


def movimento(**alteracoes):
    linha = dict(origem="simulated", tipo="reta", controle="com_correcao",
                 alvo="1000", medido="1000", desvio_mm="0", colisoes="0",
                 resultado="concluido")
    linha.update(alteracoes)
    return linha


def autonomia(**alteracoes):
    linhas = [dict(t_s=str(t), origem="simulated", estado="executando", tensao_v="8",
                   corrente_a="1", temperatura_c="30", resets="0", quedas_link="0")
              for t in range(0, 1801, 60)]
    linhas[-1].update(alteracoes)
    return linhas


def analisar(linhas):
    return analisar_autonomia(linhas, 60, 6.3, 60)


class TestCalibracao(unittest.TestCase):
    def test_diametro_por_referencia_externa(self):
        self.assertAlmostEqual(diametro_por_volta(100, 960, 960), 100 / math.pi)
        self.assertAlmostEqual(diametro_por_volta(100, -960, 960), 100 / math.pi)

    def test_distancia_rodas_corrigida(self):
        self.assertAlmostEqual(distancia_rodas_corrigida(100, 90, 100), 90)
        self.assertAlmostEqual(distancia_rodas_corrigida(100, -90, -100), 90)

    def test_calibracao_nao_aceita_medicao_nula_ou_sinal_incoerente(self):
        for args in ((0, 1, 1), (1, 0, 1), (1, 1, 0), (-1, 1, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                diametro_por_volta(*args)
        for args in ((100, 0, 90), (100, 90, 0), (100, -90, 90), (0, 90, 90)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                distancia_rodas_corrigida(*args)

    def test_erros_dispersao_e_sucesso(self):
        r = analisar_movimentos([movimento(medido="990"), movimento(medido="1010")], 10, 2, 5)
        grupo = r["grupos"][0]
        self.assertEqual(grupo["erro_medio"], 0)
        self.assertEqual(grupo["erro_absoluto_medio"], 10)
        self.assertAlmostEqual(grupo["desvio_padrao"], math.sqrt(200))
        self.assertEqual(grupo["taxa_sucesso"], 1)

    def test_nao_mistura_controles_origens_tipos_ou_alvos(self):
        linhas = [movimento(), movimento(controle="sem_correcao"),
                  movimento(origem="measured"), movimento(tipo="giro", alvo="90", medido="90"),
                  movimento(alvo="500", medido="500")]
        self.assertEqual(len(analisar_movimentos(linhas, 10, 2, 5)["grupos"]), 5)

    def test_falha_colisao_e_desvio_reprovam_mesmo_com_alvo_correto(self):
        linhas = [movimento(colisoes="1"), movimento(desvio_mm="6"),
                  movimento(resultado="falha"), movimento(resultado="interrompido")]
        g = analisar_movimentos(linhas, 10, 2, 5)["grupos"][0]
        self.assertEqual(g["sucessos"], 0)
        self.assertEqual(g["colisoes"], 1)

    def test_giro_nao_esconde_volta_extra(self):
        g = analisar_movimentos([movimento(tipo="giro", alvo="90", medido="450")], 10, 2, 5)["grupos"][0]
        self.assertEqual(g["erro_medio"], 360)
        self.assertEqual(g["sucessos"], 0)

    def test_um_ensaio_nao_inventa_dispersao(self):
        self.assertIsNone(analisar_movimentos([movimento()], 10, 2, 5)["grupos"][0]["desvio_padrao"])

    def test_formulario_vazio_nao_e_evidencia(self):
        with self.assertRaises(ValueError):
            analisar_movimentos([], 10, 2, 5)

    def test_rejeita_movimento_invalido(self):
        for alteracao in (dict(origem="estimated"), dict(tipo="outro"), dict(controle="x"),
                          dict(resultado="ok"), dict(alvo="0"), dict(medido="nan"),
                          dict(colisoes="0.5"), dict(desvio_mm="-1")):
            with self.subTest(alteracao=alteracao), self.assertRaises(ValueError):
                analisar_movimentos([movimento(**alteracao)], 10, 2, 5)
        with self.assertRaises(ValueError):
            analisar_movimentos([movimento()], -1, 2, 5)

    def test_trinta_minutos_e_energia_trapezoidal(self):
        r = analisar(autonomia())
        self.assertTrue(r["criterios_observaveis_atendidos"])
        self.assertEqual(r["origem"], "simulated")
        self.assertEqual(r["duracao_s"], 1800)
        self.assertAlmostEqual(r["energia_wh"], 4)

    def test_potencia_variavel_usando_integracao_trapezoidal(self):
        linhas = autonomia()
        linhas[-1]["corrente_a"] = "2"
        self.assertAlmostEqual(analisar(linhas)["energia_wh"], 4 + 4 * 60 / 3600)

    def test_corrente_ausente_nao_inventa_consumo(self):
        r = analisar(autonomia(corrente_a=""))
        self.assertIsNone(r["energia_wh"])
        self.assertTrue(r["criterios_observaveis_atendidos"])

    def test_dois_pontos_distantes_nao_comprovam_operacao_continua(self):
        linhas = autonomia()
        r = analisar([linhas[0], linhas[-1]])
        self.assertFalse(r["criterios_observaveis_atendidos"])
        self.assertIn("lacuna de coleta acima do limite", r["pendencias"])

    def test_ensaio_curto(self):
        self.assertIn("duracao inferior a 30 minutos", analisar(autonomia()[:-1])["pendencias"])

    def test_reset_queda_parada_e_limites_impedem_aprovacao(self):
        for alteracao in (dict(resets="1"), dict(quedas_link="1"), dict(estado="parado"),
                          dict(estado="falha"), dict(tensao_v="6"), dict(temperatura_c="61"),
                          dict(tensao_v=""), dict(temperatura_c="")):
            with self.subTest(alteracao=alteracao):
                self.assertFalse(analisar(autonomia(**alteracao))["criterios_observaveis_atendidos"])

    def test_tempo_duplicado_reverso_ou_origem_mista(self):
        for alteracao in (dict(t_s="0"), dict(t_s="1740"), dict(origem="measured")):
            with self.subTest(alteracao=alteracao), self.assertRaises(ValueError):
                analisar(autonomia(**alteracao))

    def test_contadores_nao_podem_diminuir(self):
        for campo in ("resets", "quedas_link"):
            linhas = autonomia()
            linhas[0][campo] = "1"
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                analisar(linhas)

    def test_rejeita_amostras_invalidas(self):
        for alteracao in (dict(t_s="nan"), dict(tensao_v="inf"), dict(corrente_a="-1"),
                          dict(temperatura_c="-300"), dict(resets="0.5"), dict(estado="x")):
            with self.subTest(alteracao=alteracao), self.assertRaises(ValueError):
                analisar(autonomia(**alteracao))
        for linhas in ([], autonomia()[:1]):
            with self.assertRaises(ValueError):
                analisar(linhas)

    def test_csv_cabecalho_e_colunas(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'teste.csv'
            cabecalho = ','.join(CAMPOS_MOVIMENTO)
            for texto in ('errado\n', cabecalho + '\nsimulated,reta\n',
                          cabecalho + '\nsimulated,reta,com_correcao,1,1,0,0,concluido,extra\n'):
                caminho.write_text(texto, encoding='utf-8')
                with self.subTest(texto=texto), self.assertRaises(ValueError):
                    ler_csv(caminho, CAMPOS_MOVIMENTO)

    def test_cli_csv_ate_json(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'movimentos.csv'
            caminho.write_text(','.join(CAMPOS_MOVIMENTO) + '\n'
                               + ','.join(movimento().values()) + '\n', encoding='utf-8-sig')
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                main(['movimentos', str(caminho), '--tolerancia-reta-mm', '10',
                      '--tolerancia-giro-graus', '2', '--desvio-max-mm', '5'])
            self.assertEqual(json.loads(buffer.getvalue())["grupos"][0]["taxa_sucesso"], 1)


if __name__ == '__main__':
    unittest.main()
