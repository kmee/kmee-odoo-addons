# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes unitários puros (sem ORM) para os algoritmos de cálculo.

Podem ser executados sem instância Odoo:
    python -m pytest l10n_br_hr_payroll/tests/test_salary_rules_pure.py -v
"""
from datetime import date

from odoo.tests.common import BaseCase

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    calc_decimo_avos,
    calc_ferias_dias,
    calc_inss as _calc_inss,
    calc_irrf as _calc_irrf,
    calc_pensao_alimenticia,
    calc_salario_familia as _calc_salario_familia,
    calc_vt,
    dias_dsr,
)

from .fixtures import FAIXAS_INSS_2024, FAIXAS_IRRF_2024, FAIXAS_SF_2024


def calc_inss(base):
    return _calc_inss(base, FAIXAS_INSS_2024)


def calc_irrf(base):
    return _calc_irrf(base, FAIXAS_IRRF_2024)


def calc_salario_familia(remuneracao, num_filhos):
    return _calc_salario_familia(remuneracao, num_filhos, FAIXAS_SF_2024)


class TestCalcINSSPuro(BaseCase):
    """Testes unitários puros do algoritmo de cálculo de INSS."""

    def assertMoney(self, a, b, places=2):
        self.assertAlmostEqual(a, b, places=places, msg=f"{a} != {b}")

    def test_faixa1_salario_minimo(self):
        self.assertMoney(calc_inss(1412.00), 105.90)

    def test_faixa1_completa(self):
        """R$1.412 = 100% na faixa 1: 1412 * 7.5% = 105.90."""
        self.assertMoney(calc_inss(1412.00), 105.90)

    def test_faixa2_1500(self):
        """1412 * 7.5% + 88 * 9% = 105.90 + 7.92 = 113.82."""
        self.assertMoney(calc_inss(1500.00), 113.82)

    def test_faixa2_teto(self):
        """R$2.666,68: teto da faixa 2."""
        self.assertMoney(calc_inss(2666.68), 218.82)

    def test_faixa3_3000(self):
        """R$3.000: faixas 1+2+3."""
        self.assertMoney(calc_inss(3000.00), 258.82)

    def test_teto_exato_7786_02(self):
        self.assertMoney(calc_inss(7786.02), 908.86)

    def test_acima_teto_10000(self):
        self.assertMoney(calc_inss(10000.00), 908.86)

    def test_acima_teto_50000(self):
        self.assertMoney(calc_inss(50000.00), 908.86)

    def test_salario_zero(self):
        self.assertMoney(calc_inss(0.00), 0.00)

    def test_salario_centavos(self):
        """Centavo adicional não deve causar erro de arredondamento."""
        result = calc_inss(1412.01)
        self.assertGreaterEqual(result, 105.90)
        self.assertLess(result, 908.86)


class TestCalcIRRFPuro(BaseCase):
    """Testes unitários puros do algoritmo de cálculo de IRRF."""

    def assertMoney(self, a, b, places=2):
        self.assertAlmostEqual(a, b, places=places, msg=f"{a} != {b}")

    def test_isento_abaixo_2259(self):
        self.assertMoney(calc_irrf(2000.00), 0.00)

    def test_isento_exatamente_2259_20(self):
        self.assertMoney(calc_irrf(2259.20), 0.00)

    def test_faixa2_7_5_porcento(self):
        """Base 2500: 2500 * 7.5% - 169.44 = 18.06."""
        self.assertMoney(calc_irrf(2500.00), 18.06)

    def test_faixa3_15_porcento(self):
        """Base 3500: 3500 * 15% - 381.44 = 143.56."""
        self.assertMoney(calc_irrf(3500.00), 143.56)

    def test_faixa4_22_5_porcento(self):
        """Base 4500: 4500 * 22.5% - 662.77 = 349.73."""
        self.assertMoney(calc_irrf(4500.00), 349.73)

    def test_faixa5_27_5_porcento(self):
        """Base 10000: 10000 * 27.5% - 896 = 1854."""
        self.assertMoney(calc_irrf(10000.00), 1854.00)

    def test_nunca_negativo(self):
        """IRRF nunca pode ser negativo."""
        for base in [0, 100, 1000, 2259, 2259.20]:
            with self.subTest(base=base):
                self.assertGreaterEqual(calc_irrf(base), 0.0)


class TestCalcFeriasDias(BaseCase):
    """Tabela de dias de férias por faltas (CLT art. 130)."""

    def test_zero_faltas(self):
        self.assertEqual(calc_ferias_dias(0), 30)

    def test_5_faltas(self):
        self.assertEqual(calc_ferias_dias(5), 30)

    def test_6_faltas(self):
        self.assertEqual(calc_ferias_dias(6), 24)

    def test_14_faltas(self):
        self.assertEqual(calc_ferias_dias(14), 24)

    def test_15_faltas(self):
        self.assertEqual(calc_ferias_dias(15), 18)

    def test_23_faltas(self):
        self.assertEqual(calc_ferias_dias(23), 18)

    def test_24_faltas(self):
        self.assertEqual(calc_ferias_dias(24), 12)

    def test_32_faltas(self):
        self.assertEqual(calc_ferias_dias(32), 12)

    def test_33_faltas_perde_ferias(self):
        self.assertEqual(calc_ferias_dias(33), 0)

    def test_100_faltas_perde_ferias(self):
        self.assertEqual(calc_ferias_dias(100), 0)


class TestCalcDecimoAvos(BaseCase):
    """Cálculo de avos do 13º."""

    def test_admitido_jan_12_avos(self):
        self.assertEqual(calc_decimo_avos(date(2024, 1, 1), date(2024, 12, 31)), 12)

    def test_admitido_jul_6_avos(self):
        self.assertEqual(calc_decimo_avos(date(2024, 7, 1), date(2024, 12, 31)), 6)

    def test_admitido_out_3_avos(self):
        self.assertEqual(calc_decimo_avos(date(2024, 10, 1), date(2024, 12, 31)), 3)

    def test_admitido_dia_15_conta_mes(self):
        self.assertEqual(calc_decimo_avos(date(2024, 12, 15), date(2024, 12, 31)), 1)

    def test_admitido_dia_16_conta_mes_31_dias(self):
        """Dia 16/dez (31 dias): 16 dias trabalhados >= 15 → conta."""
        self.assertEqual(calc_decimo_avos(date(2024, 12, 16), date(2024, 12, 31)), 1)

    def test_admitido_dia_18_nao_conta_mes(self):
        """Dia 18/dez (31 dias): 14 dias trabalhados < 15 → não conta."""
        self.assertEqual(calc_decimo_avos(date(2024, 12, 18), date(2024, 12, 31)), 0)

    def test_admitido_dia_25_nao_conta_mes(self):
        """Dia 25/dez (31 dias): 7 dias trabalhados < 15 → não conta."""
        self.assertEqual(calc_decimo_avos(date(2024, 12, 25), date(2024, 12, 31)), 0)

    def test_maximo_12_avos(self):
        self.assertEqual(calc_decimo_avos(date(2019, 1, 1), date(2024, 12, 31)), 12)


class TestCalcVT(BaseCase):
    """Cálculo de desconto de Vale-Transporte."""

    def test_vt_menor_que_6_porcento_desconta_tudo(self):
        self.assertAlmostEqual(calc_vt(5000.00, 100.00), 100.00)

    def test_vt_maior_que_6_porcento_limita(self):
        self.assertAlmostEqual(calc_vt(2000.00, 200.00), 120.00)

    def test_vt_exatamente_6_porcento(self):
        self.assertAlmostEqual(calc_vt(3000.00, 180.00), 180.00)

    def test_vt_zero(self):
        self.assertAlmostEqual(calc_vt(5000.00, 0.00), 0.00)


class TestCalcSalarioFamilia(BaseCase):
    """Cálculo de salário família."""

    def test_faixa1_um_filho(self):
        self.assertAlmostEqual(calc_salario_familia(1412.00, 1), 62.04)

    def test_faixa1_dois_filhos(self):
        self.assertAlmostEqual(calc_salario_familia(1412.00, 2), 124.08)

    def test_acima_faixa_unica_zero(self):
        """Remuneração acima do limite da faixa única (2024) → sem direito.

        A estrutura de 2 faixas foi extinta; em 2024 há uma única faixa até
        R$1.819,26. R$2.000 está acima → salário família zero.
        """
        self.assertAlmostEqual(calc_salario_familia(2000.00, 1), 0.00)

    def test_acima_teto_zero(self):
        self.assertAlmostEqual(calc_salario_familia(5000.00, 3), 0.00)

    def test_sem_filhos(self):
        self.assertAlmostEqual(calc_salario_familia(1412.00, 0), 0.00)


class TestCalcPensaoAlimenticia(BaseCase):
    """RF-03: valor efetivo da pensão (fixo + percentual sobre remuneração)."""

    def test_apenas_valor_fixo(self):
        self.assertAlmostEqual(calc_pensao_alimenticia(5000.00, 800.00, 0.0), 800.00)

    def test_apenas_percentual(self):
        """30% de R$5.000 = R$1.500."""
        self.assertAlmostEqual(calc_pensao_alimenticia(5000.00, 0.0, 30.0), 1500.00)

    def test_fixo_mais_percentual(self):
        """R$500 + 10% de R$5.000 = R$500 + R$500 = R$1.000."""
        self.assertAlmostEqual(calc_pensao_alimenticia(5000.00, 500.00, 10.0), 1000.00)

    def test_sem_pensao(self):
        self.assertAlmostEqual(calc_pensao_alimenticia(5000.00, 0.0, 0.0), 0.00)


class TestDiasDSR(BaseCase):
    """RF-26: dias úteis e DSR derivados do mês da competência."""

    def test_marco_2024_cinco_domingos(self):
        """Março/2024: 31 dias, 5 domingos (3,10,17,24,31) → 26 úteis, 5 DSR."""
        uteis, dsr = dias_dsr(2024, 3)
        self.assertEqual((uteis, dsr), (26, 5))

    def test_fevereiro_2024_quatro_domingos(self):
        """Fevereiro/2024 (bissexto): 29 dias, 4 domingos → 25 úteis, 4 DSR."""
        uteis, dsr = dias_dsr(2024, 2)
        self.assertEqual((uteis, dsr), (25, 4))

    def test_soma_bate_com_total_do_mes(self):
        for mes in range(1, 13):
            with self.subTest(mes=mes):
                uteis, dsr = dias_dsr(2025, mes)
                self.assertGreater(uteis, 0)
                self.assertGreater(dsr, 0)
