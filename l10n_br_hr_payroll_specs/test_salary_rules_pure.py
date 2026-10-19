# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
Testes unitários puros (sem ORM) para os algoritmos de cálculo.

Estes testes podem ser executados sem uma instância Odoo rodando,
usando apenas 'python -m pytest' ou 'pytest'.

São os testes mais rápidos — devem rodar em < 1 segundo.
"""
import unittest

# ══════════════════════════════════════════════════════════════════
# Funções a serem implementadas em:
# l10n_br_hr_payroll/models/salary_rules_br.py
# ══════════════════════════════════════════════════════════════════


def calc_inss(salario_bruto: float, ano: int = 2024) -> float:
    """
    Calcula o INSS progressivo conforme a tabela do ano.

    Args:
        salario_bruto: Salário bruto mensal em R$
        ano: Ano de referência para a tabela

    Returns:
        Valor do desconto de INSS em R$ (positivo = desconto)
    """
    TABELAS = {
        2024: {
            "faixas": [
                (1412.00, 0.075),
                (2666.68, 0.09),
                (4000.03, 0.12),
                (7786.02, 0.14),
            ],
            "teto": 908.86,
        }
    }
    tabela = TABELAS.get(ano, TABELAS[2024])
    result = 0.0
    base_anterior = 0.0
    for limite, aliquota in tabela["faixas"]:
        if salario_bruto > base_anterior:
            base_faixa = min(salario_bruto, limite) - base_anterior
            result += base_faixa * aliquota
            base_anterior = limite
        else:
            break
    return round(min(result, tabela["teto"]), 2)


def calc_irrf(base_irrf: float, ano: int = 2024) -> float:
    """
    Calcula o IRRF sobre a base de cálculo já deduzida (pós-INSS e pós-dependentes).

    Args:
        base_irrf: Base de cálculo do IRRF (salário - INSS - dependentes - pensão)
        ano: Ano de referência

    Returns:
        Valor do desconto de IRRF em R$ (sempre >= 0)
    """
    TABELAS = {
        2024: [
            (2259.20, 0.000, 0.00),
            (2826.65, 0.075, 169.44),
            (3751.05, 0.150, 381.44),
            (4664.68, 0.225, 662.77),
            (float("inf"), 0.275, 896.00),
        ]
    }
    tabela = TABELAS.get(ano, TABELAS[2024])
    for limite, aliquota, deducao in tabela:
        if base_irrf <= limite:
            result = base_irrf * aliquota - deducao
            return round(max(0.0, result), 2)
    return 0.0


def calc_ferias_dias(faltas: int) -> int:
    """
    Retorna o número de dias de férias conforme faltas injustificadas (CLT art. 130).

    Args:
        faltas: Número de faltas injustificadas no período aquisitivo

    Returns:
        Dias de férias a que o funcionário tem direito
    """
    if faltas <= 5:
        return 30
    elif faltas <= 14:
        return 24
    elif faltas <= 23:
        return 18
    elif faltas <= 32:
        return 12
    return 0


def calc_decimo_avos(data_admissao, data_referencia) -> int:
    """
    Calcula os avos do 13º salário.

    Args:
        data_admissao: Data de admissão (date)
        data_referencia: Data de referência para o cálculo (date — geralmente 31/12)

    Returns:
        Número de avos (0 a 12)
    """
    avos = 0
    ano = data_referencia.year
    # Conta meses de janeiro ao mês da referência
    for mes in range(1, data_referencia.month + 1):
        # Verifica se o funcionário trabalhei >= 15 dias neste mês
        if data_admissao.year < ano:
            avos += 1  # Já estava antes do ano: conta o mês inteiro
        elif data_admissao.year == ano and data_admissao.month < mes:
            avos += 1  # Admitido em mês anterior: conta
        elif data_admissao.year == ano and data_admissao.month == mes:
            # Admitido neste mês: conta se dia <= 15
            if data_admissao.day <= 15:
                avos += 1
    return min(avos, 12)


def calc_vt(salario: float, valor_vt: float) -> float:
    """
    Calcula o desconto de Vale-Transporte do empregado.
    Máximo de 6% do salário, limitado ao valor do VT.

    Args:
        salario: Salário mensal
        valor_vt: Valor total do VT mensal

    Returns:
        Valor do desconto de VT a ser descontado do empregado
    """
    limite_6_porcento = salario * 0.06
    return round(min(limite_6_porcento, valor_vt), 2)


# ══════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════


class TestCalcINSSPuro(unittest.TestCase):
    """Testes unitários puros do algoritmo de cálculo de INSS."""

    def assertMoney(self, a, b, places=2):
        self.assertAlmostEqual(a, b, places=places, msg=f"{a} != {b}")

    # ── Faixas individuais ────────────────────────────────────────
    def test_faixa1_salario_minimo(self):
        self.assertMoney(calc_inss(1412.00), 105.90)

    def test_faixa1_completa(self):
        """R$1.412 = 100% na faixa 1: 1412 × 7.5% = 105.90."""
        self.assertMoney(calc_inss(1412.00), 105.90)

    def test_faixa2_1500(self):
        """1412 × 7.5% + 88 × 9% = 105.90 + 7.92 = 113.82."""
        self.assertMoney(calc_inss(1500.00), 113.82)

    def test_faixa2_teto(self):
        """R$2.666,68: teto da faixa 2."""
        self.assertMoney(calc_inss(2666.68), 218.82)

    def test_faixa3_3000(self):
        """R$3.000: faixas 1+2+3."""
        # 1412 × 7.5% = 105.90
        # 1254.68 × 9% = 112.92
        # 333.32 × 12% = 39.998 ≈ 40.00
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
        """Salário com centavos não deve causar erros de arredondamento.
        R$1.412,01: o centavo adicional entra na faixa 2 (9%), porém o
        arredondamento de 2 casas mantém o resultado em R$105,90.
        O importante é que seja >= R$105,90 e <= teto.
        """
        result = calc_inss(1412.01)
        self.assertGreaterEqual(result, 105.90)
        self.assertLess(result, 908.86)


class TestCalcIRRFPuro(unittest.TestCase):
    """Testes unitários puros do algoritmo de cálculo de IRRF."""

    def assertMoney(self, a, b, places=2):
        self.assertAlmostEqual(a, b, places=places, msg=f"{a} != {b}")

    def test_isento_abaixo_2259(self):
        self.assertMoney(calc_irrf(2000.00), 0.00)

    def test_isento_exatamente_2259_20(self):
        self.assertMoney(calc_irrf(2259.20), 0.00)

    def test_faixa2_7_5_porcento(self):
        """Base 2500: 2500 × 7.5% - 169.44 = 187.50 - 169.44 = 18.06."""
        self.assertMoney(calc_irrf(2500.00), 18.06)

    def test_faixa3_15_porcento(self):
        """Base 3500: 3500 × 15% - 381.44 = 525 - 381.44 = 143.56."""
        self.assertMoney(calc_irrf(3500.00), 143.56)

    def test_faixa4_22_5_porcento(self):
        """Base 4500: 4500 × 22.5% - 662.77 = 1012.50 - 662.77 = 349.73."""
        self.assertMoney(calc_irrf(4500.00), 349.73)

    def test_faixa5_27_5_porcento(self):
        """Base 10000: 10000 × 27.5% - 896 = 2750 - 896 = 1854."""
        self.assertMoney(calc_irrf(10000.00), 1854.00)

    def test_nunca_negativo(self):
        """IRRF nunca pode ser negativo."""
        for base in [0, 100, 1000, 2259, 2259.20]:
            with self.subTest(base=base):
                self.assertGreaterEqual(calc_irrf(base), 0.0)


class TestCalcFeriasDias(unittest.TestCase):
    """Testes da tabela de dias de férias por faltas (CLT art. 130)."""

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


class TestCalcDecimoAvos(unittest.TestCase):
    """Testes do cálculo de avos do 13º."""

    from datetime import date as _date

    def setUp(self):
        super().setUp()
        from datetime import date

        self.date = date

    def test_admitido_jan_12_avos(self):
        from datetime import date

        self.assertEqual(calc_decimo_avos(date(2024, 1, 1), date(2024, 12, 31)), 12)

    def test_admitido_jul_6_avos(self):
        from datetime import date

        self.assertEqual(calc_decimo_avos(date(2024, 7, 1), date(2024, 12, 31)), 6)

    def test_admitido_out_3_avos(self):
        from datetime import date

        self.assertEqual(calc_decimo_avos(date(2024, 10, 1), date(2024, 12, 31)), 3)

    def test_admitido_dia_15_conta_mes(self):
        from datetime import date

        # Admitido em 15/12: conta 1 avo
        self.assertEqual(calc_decimo_avos(date(2024, 12, 15), date(2024, 12, 31)), 1)

    def test_admitido_dia_16_nao_conta_mes(self):
        from datetime import date

        # Admitido em 16/12: não conta (< 15 dias restantes não é a regra exata,
        # mas a regra é: se admitido até o dia 15, conta o mês)
        self.assertEqual(calc_decimo_avos(date(2024, 12, 16), date(2024, 12, 31)), 0)

    def test_maximo_12_avos(self):
        from datetime import date

        # Mesmo admitido há 5 anos, máximo é 12
        self.assertEqual(calc_decimo_avos(date(2019, 1, 1), date(2024, 12, 31)), 12)


class TestCalcVT(unittest.TestCase):
    """Testes do cálculo de desconto de Vale-Transporte."""

    def test_vt_menor_que_6_porcento_desconta_tudo(self):
        """Se o VT custar menos que 6% do salário, desconta o valor total do VT."""
        # 6% de 5000 = 300; VT é 100 < 300 → desconta 100
        self.assertAlmostEqual(calc_vt(5000.00, 100.00), 100.00)

    def test_vt_maior_que_6_porcento_limita(self):
        """Se VT > 6% do salário, desconta apenas 6%."""
        # 6% de 2000 = 120; VT é 200 > 120 → desconta 120
        self.assertAlmostEqual(calc_vt(2000.00, 200.00), 120.00)

    def test_vt_exatamente_6_porcento(self):
        """VT exatamente 6% do salário → desconta o VT inteiro."""
        self.assertAlmostEqual(calc_vt(3000.00, 180.00), 180.00)

    def test_vt_zero(self):
        """Sem VT → sem desconto."""
        self.assertAlmostEqual(calc_vt(5000.00, 0.00), 0.00)


if __name__ == "__main__":
    unittest.main(verbosity=2)
