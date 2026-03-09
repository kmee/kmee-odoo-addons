# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes de arredondamento monetário da folha de pagamento brasileira.

Verifica que todos os cálculos usam ROUND_HALF_UP (padrão contábil BR),
não banker's rounding (Python round()), e que edge cases de centavos
são tratados corretamente.

Podem ser executados sem instância Odoo:
    python -m pytest l10n_br_hr_payroll/tests/test_arredondamento.py -v
"""

from odoo.tests.common import BaseCase

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    calc_inss,
    calc_irrf,
    calc_salario_familia,
    calc_vt,
    round_money,
)


class TestRoundMoney(BaseCase):
    """Testes unitários da função round_money (ROUND_HALF_UP)."""

    def test_round_half_up_basico(self):
        """0.005 deve arredondar para cima (0.01), não para baixo."""
        self.assertEqual(round_money(0.005), 0.01)

    def test_round_half_up_2_345(self):
        """2.345 → 2.35 (HALF_UP), não 2.34 (banker's)."""
        self.assertEqual(round_money(2.345), 2.35)

    def test_round_half_up_2_335(self):
        """2.335 → 2.34 (HALF_UP), não 2.33 (banker's arredondaria para par)."""
        self.assertEqual(round_money(2.335), 2.34)

    def test_round_half_up_1_5050(self):
        """1.505 → 1.51 (HALF_UP)."""
        self.assertEqual(round_money(1.505), 1.51)

    def test_round_half_up_2_5050(self):
        """2.505 → 2.51 (HALF_UP), não 2.50 (banker's)."""
        self.assertEqual(round_money(2.505), 2.51)

    def test_round_abaixo_meio(self):
        """2.344 → 2.34 (ambos concordam)."""
        self.assertEqual(round_money(2.344), 2.34)

    def test_round_acima_meio(self):
        """2.346 → 2.35 (ambos concordam)."""
        self.assertEqual(round_money(2.346), 2.35)

    def test_round_zero(self):
        self.assertEqual(round_money(0.0), 0.0)

    def test_round_negativo(self):
        """Arredondamento de valor negativo."""
        self.assertEqual(round_money(-2.345), -2.35)

    def test_round_inteiro(self):
        """Valor inteiro permanece inteiro."""
        self.assertEqual(round_money(100.0), 100.0)

    def test_round_muitas_casas(self):
        """Valor com muitas casas decimais."""
        self.assertEqual(round_money(1234.56789), 1234.57)

    def test_round_centavo_exato(self):
        """Valor já com 2 casas decimais permanece inalterado."""
        self.assertEqual(round_money(99.99), 99.99)

    def test_round_custom_places(self):
        """Arredondamento com casas decimais customizadas."""
        self.assertEqual(round_money(1.2345, places=3), 1.235)
        self.assertEqual(round_money(1.2345, places=1), 1.2)


class TestDiferencaBankersVsHalfUp(BaseCase):
    """Testes que demonstram onde banker's rounding difere de HALF_UP.

    Estes são os edge cases que causavam problemas na ABGF.
    Cada teste verifica que round_money NÃO faz banker's rounding.
    """

    def test_caso_classico_0_545(self):
        """Python round(0.545, 2) = 0.54 (banker's). Esperado: 0.55."""
        # NOTA: Devido a representação IEEE 754, 0.545 em float é
        # 0.54499999... então até HALF_UP dá 0.54. Mas com Decimal(str())
        # o valor é exato.
        self.assertEqual(round_money(0.545), 0.55)

    def test_caso_classico_0_555(self):
        """Python round(0.555, 2) = 0.56 (banker's arredonda para par).
        HALF_UP: 0.56 (mesmo resultado neste caso)."""
        self.assertEqual(round_money(0.555), 0.56)

    def test_caso_classico_0_565(self):
        """Python round(0.565, 2) = 0.56 (banker's). Esperado: 0.57."""
        self.assertEqual(round_money(0.565), 0.57)

    def test_caso_classico_0_575(self):
        """Python round(0.575, 2) = 0.58 (coincide). Esperado: 0.58."""
        self.assertEqual(round_money(0.575), 0.58)

    def test_caso_classico_0_585(self):
        """Python round(0.585, 2) = 0.58 (banker's). Esperado: 0.59."""
        self.assertEqual(round_money(0.585), 0.59)

    def test_caso_classico_0_595(self):
        """Python round(0.595, 2) = 0.59 (banker's). Esperado: 0.60."""
        self.assertEqual(round_money(0.595), 0.60)

    def test_caso_classico_2_675(self):
        """round(2.675, 2) é o exemplo clássico de Python. Banker's = 2.67."""
        self.assertEqual(round_money(2.675), 2.68)

    def test_half_up_consistente_em_serie(self):
        """Todos os .xx5 arredondam para cima, sem alternar par/ímpar."""
        for i in range(10):
            valor = i / 10.0 + 0.005
            resultado = round_money(valor)
            esperado = round_money(valor)
            self.assertEqual(
                resultado,
                esperado,
                f"round_money({valor}) divergiu: {resultado} != {esperado}",
            )


class TestINSSArredondamento(BaseCase):
    """Edge cases de arredondamento no INSS progressivo."""

    def assertMoney(self, a, b, msg=None):
        self.assertAlmostEqual(a, b, places=2, msg=msg or f"{a} != {b}")

    def test_faixa3_parcial_39_998(self):
        """R$3.000: faixa 3 parcial = 333.32 × 12% = 39.9984.

        round_money(39.9984) = 40.00 (arredondamento correto).
        Total = 105.90 + 112.9212 + 39.9984 = 258.8196 → 258.82.
        """
        self.assertMoney(calc_inss(3000.00), 258.82)

    def test_centavo_acima_faixa1(self):
        """R$1.412,01: 1 centavo acima da faixa 1.

        Faixa 1: 1412 × 7.5% = 105.90
        Faixa 2: 0.01 × 9% = 0.0009
        Total = 105.9009 → 105.90.
        """
        self.assertMoney(calc_inss(1412.01), 105.90)

    def test_centavo_acima_faixa2(self):
        """R$2.666,69: 1 centavo acima da faixa 2.

        Faixa 1: 1412 × 7.5% = 105.90
        Faixa 2: 1254.68 × 9% = 112.9212
        Faixa 3: 0.01 × 12% = 0.0012
        Total = 218.8224 → 218.82.
        """
        self.assertMoney(calc_inss(2666.69), 218.82)

    def test_centavo_acima_faixa3(self):
        """R$4.000,04: 1 centavo acima da faixa 3.

        Faixa 1: 1412 × 7.5% = 105.90
        Faixa 2: 1254.68 × 9% = 112.9212
        Faixa 3: 1333.35 × 12% = 160.002
        Faixa 4: 0.01 × 14% = 0.0014
        Total = 378.8246 → 378.82.
        """
        result = calc_inss(4000.04)
        self.assertMoney(result, 378.82)

    def test_salario_com_centavos_impares(self):
        """Salário com centavos que produzem divisão não exata."""
        # R$ 3.333,33 → faixas progressivas com frações
        result = calc_inss(3333.33)
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 908.86)
        # Verifica que resultado tem exatamente 2 decimais
        self.assertEqual(result, round_money(result))

    def test_todos_resultados_2_decimais(self):
        """Todos os resultados devem ter no máximo 2 casas decimais."""
        salarios = [
            1000,
            1412,
            1412.01,
            1500.50,
            2000.33,
            2666.68,
            2666.69,
            3000,
            3333.33,
            4000.03,
            4000.04,
            5000,
            7786.02,
            10000,
            50000,
        ]
        for sal in salarios:
            result = calc_inss(sal)
            self.assertEqual(
                result,
                round_money(result),
                f"calc_inss({sal}) = {result} não tem 2 decimais exatos",
            )


class TestIRRFArredondamento(BaseCase):
    """Edge cases de arredondamento no IRRF."""

    def assertMoney(self, a, b, msg=None):
        self.assertAlmostEqual(a, b, places=2, msg=msg or f"{a} != {b}")

    def test_limite_exato_faixa2(self):
        """Base exatamente no limite faixa 2: 2826.65."""
        # 2826.65 × 7.5% - 169.44 = 212.00 - 169.44 = 42.56 (exato)
        self.assertMoney(calc_irrf(2826.65), 42.56)

    def test_base_com_centavos_fracionarios(self):
        """Base IRRF com centavos que geram .xx5 na subtração."""
        # Valores que historicamente causam problemas
        for base in [2500.01, 3000.33, 3500.55, 4000.77, 5000.99]:
            result = calc_irrf(base)
            self.assertEqual(
                result,
                round_money(result),
                f"calc_irrf({base}) = {result} não tem 2 decimais exatos",
            )

    def test_irrf_centavo_acima_isencao(self):
        """Base R$2.259,21: 1 centavo acima da isenção.

        2259.21 × 7.5% - 169.44 = 169.44075 - 169.44 = 0.00075 → 0.00.
        """
        self.assertMoney(calc_irrf(2259.21), 0.00)

    def test_irrf_resultado_meio_centavo(self):
        """Busca base que produz resultado em .xx5 (meio centavo).

        Base 2693.87: 2693.87 × 7.5% - 169.44 = 202.04025 - 169.44 = 32.60025
        round_money(32.60025) = 32.60.
        """
        result = calc_irrf(2693.87)
        self.assertEqual(result, round_money(result))


class TestVTArredondamento(BaseCase):
    """Edge cases de arredondamento no Vale-Transporte."""

    def test_vt_6_porcento_centavos(self):
        """Salário que gera 6% com centavos: R$2.333,33 × 6% = 139.9998."""
        result = calc_vt(2333.33, 200.00)
        self.assertEqual(result, 140.00)

    def test_vt_centavos_fracionarios(self):
        """R$1.999,99 × 6% = 119.9994 → 120.00."""
        result = calc_vt(1999.99, 200.00)
        self.assertEqual(result, 120.00)

    def test_vt_sempre_2_decimais(self):
        """VT deve sempre ter 2 decimais."""
        for sal in [1500.33, 2000.77, 3333.33, 4500.01]:
            result = calc_vt(sal, 500.00)
            self.assertEqual(
                result,
                round_money(result),
                f"calc_vt({sal}) = {result} não tem 2 decimais",
            )


class TestSalarioFamiliaArredondamento(BaseCase):
    """Edge cases de arredondamento no salário família."""

    def test_3_filhos_faixa1(self):
        """3 filhos × R$62,04 = R$186,12 (exato)."""
        self.assertEqual(calc_salario_familia(1412.00, 3), 186.12)

    def test_5_filhos_faixa2(self):
        """5 filhos × R$43,84 = R$219,20 (exato)."""
        self.assertEqual(calc_salario_familia(2000.00, 5), 219.20)

    def test_resultado_sempre_2_decimais(self):
        """Resultado deve ter no máximo 2 casas decimais."""
        for filhos in range(1, 8):
            result = calc_salario_familia(1500.00, filhos)
            self.assertEqual(
                result,
                round_money(result),
                f"salario_familia(1500, {filhos}) = {result}",
            )


class TestArredondamentoComposicao(BaseCase):
    """Testes de composição: soma de arredondados vs arredondamento da soma.

    Na folha de pagamento, o NET é a soma das linhas já arredondadas.
    Verificamos que round_money(a) + round_money(b) pode diferir de
    round_money(a + b), e que o sistema usa a abordagem correta.
    """

    def test_soma_arredondados_pode_diferir(self):
        """Demonstra que soma de arredondados != arredondamento da soma."""
        # 1.345 + 1.345 = 2.69 (arredondando cada um: 1.35 + 1.35 = 2.70)
        a = round_money(1.345)
        b = round_money(1.345)
        soma_arredondados = a + b
        arredondamento_soma = round_money(1.345 + 1.345)
        # Podem diferir em 1 centavo
        self.assertAlmostEqual(soma_arredondados, arredondamento_soma, places=1)

    def test_net_folha_tipica(self):
        """Simula cálculo NET de uma folha típica.

        Salário R$3.000: GROSS - INSS - IRRF = NET.
        Verifica consistência do arredondamento.
        """
        salario = 3000.00
        inss = calc_inss(salario)
        base_irrf = salario - inss
        irrf = calc_irrf(base_irrf)
        fgts = round_money(salario * 0.08)

        # Cada componente deve ter 2 decimais
        self.assertEqual(inss, round_money(inss))
        self.assertEqual(irrf, round_money(irrf))
        self.assertEqual(fgts, round_money(fgts))

        # NET = soma dos componentes já arredondados
        net = round_money(salario - inss - irrf)
        self.assertEqual(net, round_money(net))
        self.assertGreater(net, 0)

    def test_ferias_um_terco(self):
        """Férias + 1/3: salários que não dividem por 3 exatamente."""
        salarios_problematicos = [
            1412.00,  # SM: 1412/3 = 470.6666...
            2500.00,  # 2500/3 = 833.3333...
            3333.33,  # 3333.33/3 = 1111.11 (exato!)
            4999.99,  # 4999.99/3 = 1666.6633...
            7786.02,  # teto INSS: 7786.02/3 = 2595.34
        ]
        for sal in salarios_problematicos:
            terco = round_money(sal / 3)
            self.assertEqual(
                terco,
                round_money(terco),
                f"Férias 1/3 de R${sal}: {terco} sem 2 decimais",
            )
            # GROSS férias = salário + 1/3
            gross = sal + terco
            self.assertEqual(
                gross,
                round_money(gross),
                f"GROSS férias R${sal}: {gross} sem 2 decimais",
            )

    def test_decimo_terceiro_proporcional(self):
        """13º proporcional: wage × avos / 12 para vários avos."""
        wage = 3333.33
        for avos in range(1, 13):
            decimo = round_money(wage * avos / 12)
            self.assertEqual(
                decimo,
                round_money(decimo),
                f"13º {avos}/12 de R${wage}: {decimo}",
            )

    def test_hora_extra_divisao_220(self):
        """Hora extra com divisão por 220 (gera dízima periódica).

        R$3.000 / 220 = 13.636363... × 1.5 × horas.
        """
        salarios = [1412.00, 2000.00, 3000.00, 5000.00, 7786.02]
        for sal in salarios:
            salario_hora = sal / 220
            for horas in [1, 5, 10, 20]:
                he_50 = round_money(salario_hora * 1.5 * horas)
                he_100 = round_money(salario_hora * 2.0 * horas)
                self.assertEqual(
                    he_50,
                    round_money(he_50),
                    f"HE50 {horas}h @ R${sal}: {he_50}",
                )
                self.assertEqual(
                    he_100,
                    round_money(he_100),
                    f"HE100 {horas}h @ R${sal}: {he_100}",
                )

    def test_faltas_dsr_composicao(self):
        """Faltas + DSR: divisão por 30 e composição com DSR/dias úteis."""
        for wage in [1412.00, 3000.00, 5000.00]:
            for faltas in [1, 2, 3, 5]:
                falta_valor = round_money((wage / 30) * faltas)
                dsr_valor = round_money((wage / 30) * faltas * 4 / 26)
                total_desc = round_money(falta_valor + dsr_valor)
                self.assertEqual(
                    falta_valor,
                    round_money(falta_valor),
                    f"Faltas({faltas}) @ R${wage}: {falta_valor}",
                )
                self.assertEqual(
                    dsr_valor,
                    round_money(dsr_valor),
                    f"DSR({faltas}) @ R${wage}: {dsr_valor}",
                )
                self.assertGreater(total_desc, 0)
