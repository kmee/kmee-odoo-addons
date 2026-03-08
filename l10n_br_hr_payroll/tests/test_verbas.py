# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: Verbas Salariais.

Cobertura:
  - Hora extra 50% e 100%
  - Adicional noturno (20%) e hora reduzida
  - Periculosidade (30% do salário)
  - Insalubridade (10%, 20%, 40% do salário mínimo)
  - Constraint: não acumular periculosidade + insalubridade
  - Salário família por faixa salarial
  - Faltas e DSR
  - FGTS integra hora extra
"""
from odoo.exceptions import ValidationError

from .common import PayrollCommon


class TestHoraExtra(PayrollCommon):
    """Testes de cálculo de hora extra."""

    def test_hora_extra_50_porcento(self):
        """HE em dias úteis: 150% do salário-hora."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_50")
        # (3000/220) × 1.50 × 10 = 204.55
        self.assertAlmostEqualMoney(he, 204.55)

    def test_hora_extra_100_porcento(self):
        """HE em domingo/feriado: 200% do salário-hora."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_100": 5})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_100")
        # (3000/220) × 2.00 × 5 = 136.36
        self.assertAlmostEqualMoney(he, 136.36)

    def test_hora_extra_integra_base_fgts(self):
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


class TestFaltasDSR(PayrollCommon):
    """Testes de faltas e desconto de DSR."""

    def test_faltas_desconta_do_salario(self):
        """Faltas injustificadas descontam proporcionalmente."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_faltas_injustificadas": 2})
        payslip.compute_sheet()
        faltas = self._get_line_total(payslip, "FALTAS")
        # (3000 / 30) * 2 = 200.00
        self.assertAlmostEqualMoney(faltas, 200.00)

    def test_dsr_descontado_com_faltas(self):
        """DSR é descontado proporcionalmente às faltas injustificadas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_faltas_injustificadas": 2})
        payslip.compute_sheet()
        dsr = self._get_line_total(payslip, "DESC_DSR")
        self.assertGreater(dsr, 0.0)


class TestAdicionalNoturno(PayrollCommon):
    """Testes do adicional noturno (art. 73 CLT)."""

    def test_adicional_noturno_20_porcento(self):
        """Adicional noturno = 20% sobre as horas noturnas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_noturnas": 176})
        payslip.compute_sheet()
        adicional = self._get_line_total(payslip, "ADICIONAL_NOTURNO")
        esperado = (3000.00 / 220) * 0.20 * 176
        self.assertAlmostEqualMoney(adicional, esperado)

    def test_hora_noturna_reduzida_52min30s(self):
        """Hora noturna reduzida (52min30s = 7/8 da hora normal)."""
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
        horas_computadas = payslip.l10n_br_horas_noturnas_computadas
        self.assertAlmostEqualMoney(horas_computadas, 52.5)


class TestPericulosidadeInsalubridade(PayrollCommon):
    """Testes de adicionais de risco."""

    SALARIO_MINIMO_2024 = 1412.00

    def test_periculosidade_30_porcento_do_salario(self):
        """Periculosidade = 30% do salário base."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write({"l10n_br_periculosidade": True})
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_PERICULOSIDADE")
        self.assertAlmostEqualMoney(adicional, 1500.00)

    def test_insalubridade_minimo_10_porcento(self):
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
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.10)

    def test_insalubridade_medio_20_porcento(self):
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

    def test_insalubridade_maximo_40_porcento(self):
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
        """Periculosidade e insalubridade não acumulam (Súmula 364 TST)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        with self.assertRaises(ValidationError):
            contract.write(
                {
                    "l10n_br_periculosidade": True,
                    "l10n_br_insalubridade": True,
                    "l10n_br_grau_insalubridade": "maximo",
                }
            )


class TestSalarioFamilia(PayrollCommon):
    """Testes de salário família."""

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
        self.assertEqual(sf, 0.0)
