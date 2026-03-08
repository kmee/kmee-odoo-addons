# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Verbas Salariais — Hora Extra, Adicional Noturno, Periculosidade,
Insalubridade e Salário Família.

Cobertura:
  - Hora extra 50% (dias úteis)
  - Hora extra 100% (domingo/feriado)
  - Adicional noturno (20%)
  - Periculosidade (30% do salário)
  - Insalubridade (10%, 20%, 40% do salário mínimo)
  - Impossibilidade de acumulação periculosidade + insalubridade
  - Salário família (por faixa salarial)
  - DSR sobre horas extras
"""

from odoo.exceptions import UserError, ValidationError

from .common import PayrollCommon


class TestHoraExtra(PayrollCommon):
    """Testes de cálculo de hora extra."""

    def _salario_hora(self, wage, jornada_mensal=220):
        return wage / jornada_mensal

    def test_hora_extra_50_porcento_dias_uteis(self):
        """HE em dias úteis: 150% do salário-hora."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        # Registra 10 horas extras em dias úteis
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_50")
        # Salário-hora = 3000/220 = 13.636...
        # HE 50% = 13.636 × 1.50 × 10 = 204.55
        self.assertAlmostEqualMoney(he, 204.55)

    def test_hora_extra_100_porcento_domingo(self):
        """HE em domingo/feriado: 200% do salário-hora."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_100": 5})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_100")
        # 3000/220 × 2.00 × 5 = 136.36
        self.assertAlmostEqualMoney(he, 136.36)

    def test_hora_extra_integra_base_do_fgts(self):
        """Hora extra compõe a base de cálculo do FGTS."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_50")
        fgts = self._get_line_total(payslip, "FGTS")
        # FGTS = (3000 + HE) × 8%
        self.assertAlmostEqualMoney(fgts, (3000.00 + he) * 0.08)

    def test_dsr_calculado_proporcional_as_faltas(self):
        """DSR é descontado proporcionalmente às faltas injustificadas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        # Março tem 5 domingos; 2 faltas em dias com 1 DSR cada
        payslip.write({"l10n_br_faltas_injustificadas": 2})
        payslip.compute_sheet()
        dsr = self._get_line_total(payslip, "DESC_DSR")
        # DSR = (salário / dias úteis) × DSR_perdido
        self.assertGreater(
            abs(dsr), 0.0, msg="Desconto de DSR deve ser maior que zero com faltas"
        )


class TestAdicionalNoturno(PayrollCommon):
    """Testes do adicional noturno (art. 73 CLT)."""

    def test_adicional_noturno_20_porcento(self):
        """Adicional noturno = 20% sobre as horas de 22h às 05h."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        # 8 horas noturnas por dia × 22 dias = 176 horas noturnas
        payslip.write({"l10n_br_horas_noturnas": 176})
        payslip.compute_sheet()
        adicional = self._get_line_total(payslip, "ADICIONAL_NOTURNO")
        # Salário-hora noturno = (3000/220) × 0.20 × 176
        esperado = (3000.00 / 220) * 0.20 * 176
        self.assertAlmostEqualMoney(adicional, esperado)

    def test_hora_noturna_reduzida_52min30s(self):
        """Hora noturna é reduzida (52min30s = 7/8 da hora normal)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write(
            {
                "l10n_br_horas_noturnas": 60,
                "l10n_br_usar_hora_reduzida": True,
            }
        )
        payslip.compute_sheet()
        # Com hora reduzida, 60 horas noturnas equivalem a 60 × (7/8) = 52.5 horas normais
        horas_computadas = payslip.l10n_br_horas_noturnas_computadas
        self.assertAlmostEqualMoney(horas_computadas, 52.5)


class TestPericulosidadeInsalubridade(PayrollCommon):
    """Testes de adicionais de risco."""

    SALARIO_MINIMO_2024 = 1412.00

    def test_periculosidade_30_porcento_do_salario(self):
        """Periculosidade = 30% do salário base (não do mínimo)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write({"l10n_br_periculosidade": True})
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_PERICULOSIDADE")
        # 30% de 5000 = 1500
        self.assertAlmostEqualMoney(adicional, 1500.00)

    def test_insalubridade_minimo_10_porcento_salario_minimo(self):
        """Insalubridade grau mínimo = 10% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "minimo",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        # 10% de R$ 1.412,00 = R$ 141,20
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.10)

    def test_insalubridade_medio_20_porcento_salario_minimo(self):
        """Insalubridade grau médio = 20% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "medio",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.20)

    def test_insalubridade_maximo_40_porcento_salario_minimo(self):
        """Insalubridade grau máximo = 40% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "maximo",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.40)

    def test_periculosidade_e_insalubridade_nao_acumulam(self):
        """Periculosidade e insalubridade não podem ser acumuladas (Súmula 364 TST)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        with self.assertRaises(
            (UserError, ValidationError),
            msg="Acúmulo de periculosidade + insalubridade deve ser rejeitado",
        ):
            contract.write(
                {
                    "l10n_br_periculosidade": True,
                    "l10n_br_insalubridade": True,
                    "l10n_br_grau_insalubridade": "maximo",
                }
            )
            contract._validate_adicionais_risco()


class TestSalarioFamilia(PayrollCommon):
    """Testes de salário família (Lei 4.266/63)."""

    def test_salario_familia_faixa1(self):
        """Salário até R$1.869,34: R$62,04 por filho."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 62.04)

    def test_salario_familia_faixa1_dois_filhos(self):
        """2 filhos na faixa 1: R$124,08 (2 × R$62,04)."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 2})
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 124.08)

    def test_salario_familia_faixa2(self):
        """Salário entre R$1.869,35 e R$2.903,98: R$43,84 por filho."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=2000.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 43.84)

    def test_salario_familia_acima_teto_zero(self):
        """Salário acima de R$2.903,98: sem salário família."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 3})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertEqual(sf, 0.0, msg="Acima do teto, salário família deve ser zero")

    def test_salario_familia_filho_acima_14_anos_nao_conta(self):
        """Filho acima de 14 anos não gera salário família."""
        emp = self._create_employee()
        # 1 filho menor de 14, 1 filho com 15 anos
        emp.write(
            {
                "l10n_br_num_filhos_sf": 1,  # apenas os válidos
                "l10n_br_filhos_invalidos_sf": 1,  # inválidos (>14 anos)
            }
        )
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        # Apenas 1 filho válido
        self.assertAlmostEqualMoney(sf, 62.04)
