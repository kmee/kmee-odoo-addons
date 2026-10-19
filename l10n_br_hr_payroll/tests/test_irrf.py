# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: IRRF com tabela progressiva 2024.

Cobertura:
  - Isenção (abaixo do limite)
  - Cada faixa da tabela progressiva
  - Dedução por dependentes
  - Dedução de pensão alimentícia
  - Isenção por moléstia grave
"""
from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    calc_irrf as _calc_irrf,
)

from .common import PayrollCommon
from .fixtures import FAIXAS_IRRF_2024


def calc_irrf(base):
    return _calc_irrf(base, FAIXAS_IRRF_2024)


# Desconto simplificado 2024 = 25% do teto da faixa de isenção (2.259,20).
DESCONTO_SIMPLIFICADO_2024 = round(0.25 * 2259.20, 2)  # 564.80


def irrf_favoravel(gross, deducoes_legais):
    """IRRF mensal pela forma mais favorável (RF-16): min(legal, simplificado).

    Espelha a regra salarial: base legal = gross - deduções legais; base
    simplificada = gross - desconto simplificado; retenção = menor imposto.
    """
    base_legal = max(gross - deducoes_legais, 0.0)
    base_simpl = max(gross - DESCONTO_SIMPLIFICADO_2024, 0.0)
    return min(calc_irrf(base_legal), calc_irrf(base_simpl))


class TestIRRFTabela(PayrollCommon):
    """Testes da tabela progressiva do IRRF sem dependentes."""

    def test_irrf_isento_abaixo_do_limite(self):
        """Salário que resulte em base IRRF abaixo de R$2.259,20 → IRRF zero."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2200.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertEqual(irrf, 0.0)

    def test_irrf_faixa2_7_5_porcento(self):
        """Base na faixa de 7,5% pela dedução legal.

        Com poucas deduções o desconto simplificado (RF-16) é mais favorável,
        então a retenção efetiva é o menor imposto entre as duas formas.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2700.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(irrf, irrf_favoravel(2700.00, inss))

    def test_irrf_faixa3_15_porcento(self):
        """Base na faixa de 15% (retenção pela forma mais favorável)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(irrf, irrf_favoravel(3500.00, inss))

    def test_irrf_faixa4_22_5_porcento(self):
        """Base na faixa de 22,5% (retenção pela forma mais favorável)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(irrf, irrf_favoravel(4500.00, inss))

    def test_irrf_faixa5_27_5_porcento(self):
        """Base na faixa de 27,5%: dedução legal ganha (INSS alto).

        Para salário alto a dedução legal (INSS no teto) supera o desconto
        simplificado, então a retenção efetiva usa a base legal.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=10000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        base = 10000.00 - inss
        irrf_esperado = base * 0.275 - 896.00
        # Aqui a forma legal é a mais favorável.
        self.assertAlmostEqualMoney(irrf, irrf_favoravel(10000.00, inss))
        self.assertAlmostEqualMoney(irrf, irrf_esperado)


class TestIRRFDependentes(PayrollCommon):
    """Testes da dedução por dependentes no IRRF."""

    def test_irrf_um_dependente_reduz_base(self):
        """1 dependente reduz a base do IRRF em R$189,59."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 1})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        base_com_dep = 5000.00 - inss - 189.59
        irrf_esperado = calc_irrf(base_com_dep)
        self.assertAlmostEqualMoney(irrf, irrf_esperado)

    def test_irrf_dois_dependentes_reduz_base(self):
        """2 dependentes deduzem R$379,18 (2 × R$189,59)."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 2})
        contract = self._create_contract(emp, wage=4000.00)
        payslip = self._create_payslip(emp, contract)
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        inss = self._get_line_total(payslip, "INSS")
        base_esperada = 4000.00 - inss - (2 * 189.59)
        self.assertAlmostEqualMoney(base_irrf, base_esperada)

    def test_irrf_dependentes_podem_tornar_isento(self):
        """Dependentes podem tornar a base abaixo do limite → IRRF zero."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 5})
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        # Com 5 dependentes: base = 3000 - INSS - 947.95 → abaixo de 2259.20
        self.assertEqual(irrf, 0.0)


class TestIRRFDeducoes(PayrollCommon):
    """Testes de deduções especiais do IRRF."""

    def test_irrf_pensao_alimenticia_dedutivel(self):
        """Pensão alimentícia judicial é deduzida da base do IRRF."""
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_alimenticia": 800.00})
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        base_esperada = 6000.00 - inss - 800.00
        self.assertAlmostEqualMoney(base_irrf, base_esperada)

    def test_irrf_molestia_grave_isencao_total(self):
        """Portador de moléstia grave (Lei 7.713/88) tem isenção total."""
        emp = self._create_employee()
        emp.write(
            {
                "l10n_br_molestia_grave": True,
                "l10n_br_cid_molestia": "C50",
            }
        )
        contract = self._create_contract(emp, wage=15000.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertEqual(irrf, 0.0)
