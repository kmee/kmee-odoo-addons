# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes do redutor do IRPF (Lei 15.270/2025) no 13º e na rescisão, e da regra
dos 15 dias no mês do desligamento (Lei 4.090/62 art. 1º §2º e art. 3º).
"""
from datetime import date

from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import calc_irrf

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestRedutorDecimoTerceiro(VacationCommon):
    """O redutor alcança o IR exclusivo de fonte do 13º salário."""

    def _payslip_13(self, wage, ano):
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=wage, date_start=date(ano - 1, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"13º {ano}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(ano, 12, 1),
                "date_to": date(ano, 12, 31),
                "struct_id": self.structure_13.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_13_de_4500_zerado_pelo_redutor_em_2026(self):
        """13º bruto de R$4.500 em 12/2026: imposto 239,92 absorvido pelo
        redutor da 1ª faixa (até R$5.000) → IRRF_13 zero.

        INSS_13 = 431,51 → base 4.068,49 → 22,5% − 675,49 = 239,92.
        Redutor máximo da faixa = 312,89 > imposto → imposto zero.
        """
        payslip = self._payslip_13(4500.00, 2026)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS_13"), 431.51)
        self.assertEqual(self._get_line_total(payslip, "IRRF_13"), 0.0)

    def test_13_de_6000_redutor_parcial_em_2026(self):
        """13º bruto de R$6.000: 564,85 − 179,75 = R$385,10."""
        payslip = self._payslip_13(6000.00, 2026)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS_13"), 641.51)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF_13"), 385.10)

    def test_13_de_8000_sem_redutor_em_2026(self):
        """13º bruto acima de R$7.350: corte seco → R$1.037,85."""
        payslip = self._payslip_13(8000.00, 2026)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF_13"), 1037.85)

    def test_13_de_4500_em_2025_sem_redutor(self):
        """Competência 12/2025: sem redutor, IRRF_13 de R$238,10 (preservado).

        INSS_13 (tabela 2025) = 439,60 → base 4.060,40 → 238,10.
        """
        payslip = self._payslip_13(4500.00, 2025)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS_13"), 439.60)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF_13"), 238.10)

    def test_base_do_redutor_do_13_e_o_bruto_do_13(self):
        """A faixa do redutor segue o BRUTO do 13º, não a base após INSS.

        13º bruto de R$7.500 (> 7.350) tem base de cálculo ~R$6.700, que
        estaria dentro da faixa do redutor. Como a lei manda usar o rendimento
        bruto, não há redutor algum.
        """
        payslip = self._payslip_13(7500.00, 2026)
        base = self._get_line_total(payslip, "BASE_IRRF_13")
        irrf = self._get_line_total(payslip, "IRRF_13")
        self.assertLess(base, 7350.00)
        faixas = self.env["l10n_br.hr.payroll.irrf.faixa"]._tabela(payslip.date_to)
        self.assertAlmostEqualMoney(irrf, calc_irrf(base, faixas))


@tagged("post_install", "-at_install")
class TestRedutorRescisao(VacationCommon):
    """Saldo de salário e 13º da rescisão também recebem o redutor."""

    def _rescisao(self, wage, date_to, date_start=None):
        emp = self._create_employee("Rescisão Redutor")
        contract = self._create_contract(
            emp, wage=wage, date_start=date_start or date(2025, 1, 1)
        )
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Rescisão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date_to.replace(day=1),
                "date_to": date_to,
                "struct_id": self.structure_rescisao.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_saldo_salario_zerado_pelo_redutor_em_2026(self):
        """Saldo de salário de R$4.500 em 2026 → IRRF zero pelo redutor."""
        payslip = self._rescisao(4500.00, date(2026, 6, 30))
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "SALDO_SALARIO"), 4500.00
        )
        self.assertEqual(self._get_line_total(payslip, "IRRF"), 0.0)

    def test_saldo_salario_com_redutor_parcial_em_2026(self):
        """Saldo de R$6.000: IRRF de R$385,10 (564,85 − 179,75)."""
        payslip = self._rescisao(6000.00, date(2026, 6, 30))
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 385.10)

    def test_rescisao_2025_sem_redutor(self):
        """Rescisão em 2025: comportamento antigo preservado."""
        payslip = self._rescisao(6000.00, date(2025, 6, 30))
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 562.63)


@tagged("post_install", "-at_install")
class TestAvos13NoDesligamento(VacationCommon):
    """Regra dos 15 dias no mês do desligamento (13º proporcional)."""

    def _rescisao_no_dia(self, dia, wage=4800.00):
        emp = self._create_employee("Rescisão Avos")
        contract = self._create_contract(emp, wage=wage, date_start=date(2023, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Rescisão dia {dia}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 6, 1),
                "date_to": date(2024, 6, dia),
                "struct_id": self.structure_rescisao.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_desligamento_dia_10_nao_gera_avo_de_junho(self):
        """Desligado em 10/06: 5 avos (jan..mai) → 4800 × 5/12 = R$2.000.

        Antes o mês do desligamento era sempre contado como avo cheio,
        pagando 6 avos (R$2.400) — 13º proporcional a mais.
        """
        payslip = self._rescisao_no_dia(10)
        self.assertEqual(payslip.l10n_br_avos_13, 5)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "DECIMO_RESCISAO"), 2000.00
        )

    def test_desligamento_dia_15_gera_avo_de_junho(self):
        """Desligado em 15/06: exatamente 15 dias → 6 avos → R$2.400."""
        payslip = self._rescisao_no_dia(15)
        self.assertEqual(payslip.l10n_br_avos_13, 6)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "DECIMO_RESCISAO"), 2400.00
        )

    def test_desligamento_dia_20_gera_avo_de_junho(self):
        """Desligado em 20/06: 20 dias → 6 avos → R$2.400."""
        payslip = self._rescisao_no_dia(20)
        self.assertEqual(payslip.l10n_br_avos_13, 6)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "DECIMO_RESCISAO"), 2400.00
        )

    def test_decimo_anual_nao_regride(self):
        """13º de dezembro fechado continua com 12 avos."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2023, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.structure_13.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        self.assertEqual(payslip.l10n_br_avos_13, 12)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "DECIMO_TERCEIRO_BRUTO"), 6000.00
        )
