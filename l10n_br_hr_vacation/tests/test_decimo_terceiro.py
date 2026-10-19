# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: 13º Salário.

Cobertura:
  - 1ª parcela (50% sem descontos)
  - 13º proporcional por avos
  - 2ª parcela (integral - 1ª parcela, com INSS/IRRF)
  - 13º na rescisão
"""
from datetime import date

from odoo.tests import tagged

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestDecimoTerceiro(VacationCommon):
    """Testes do 13º Salário."""

    def test_primeira_parcela_50_porcento(self):
        """1ª parcela do 13º = 50% do salário bruto, sem INSS/IRRF."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º Adiantamento - 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.structure_13_primeira.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        adiant = self._get_line_total(payslip, "ADIANTAMENTO_13")
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(adiant, 2500.00)
        self.assertEqual(inss, 0.0)
        self.assertEqual(irrf, 0.0)

    def _test_decimo_proporcional(
        self, date_start, expected_avos, expected_value, wage=6000.00
    ):
        """Helper para testar 13º proporcional."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=wage, date_start=date_start)
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
        avos = payslip.l10n_br_avos_13
        valor_bruto = self._get_line_total(payslip, "DECIMO_TERCEIRO_BRUTO")
        self.assertEqual(avos, expected_avos, msg=f"Avos esperados: {expected_avos}")
        self.assertAlmostEqualMoney(valor_bruto, expected_value)

    def test_decimo_12_avos(self):
        """Admitido em jan: 12 avos → 13º integral."""
        self._test_decimo_proporcional(date(2024, 1, 1), 12, 6000.00)

    def test_decimo_6_avos(self):
        """Admitido em jul: 6 avos → 50% do salário."""
        self._test_decimo_proporcional(date(2024, 7, 1), 6, 3000.00)

    def test_decimo_3_avos(self):
        """Admitido em out: 3 avos."""
        self._test_decimo_proporcional(date(2024, 10, 1), 3, 1500.00)

    def test_decimo_1_avo_admitido_16_do_mes(self):
        """Admitido no dia 16: conta 1 avo (15 dias ou mais)."""
        self._test_decimo_proporcional(date(2024, 12, 16), 1, 500.00)

    def test_decimo_zero_avos_admitido_25_do_mes(self):
        """Admitido no dia 25: não conta o mês (menos de 15 dias)."""
        self._test_decimo_proporcional(date(2024, 12, 25), 0, 0.00)

    def test_segunda_parcela_desconta_primeira(self):
        """2ª parcela = 13º integral - 1ª parcela já paga."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º 2ª Parcela - 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.structure_13_segunda.id,
                "l10n_br_primeira_parcela_13_paga": 2500.00,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        inss_13 = self._get_line_total(payslip, "INSS_13")
        irrf_13 = self._get_line_total(payslip, "IRRF_13")
        # A dedução da 1ª parcela deve existir como linha DED (ADIANTAMENTO_13),
        # não apenas no campo computado — senão paga-se o 13º em dobro.
        adiantamento_ded = self._get_line_total(payslip, "ADIANTAMENTO_13")
        net = self._get_line_total(payslip, "NET")
        liquido = payslip.l10n_br_liquido_13
        expected_liquido = 5000.00 - inss_13 - irrf_13 - 2500.00
        self.assertAlmostEqualMoney(adiantamento_ded, 2500.00)
        # O NET (linha da folha) já desconta o adiantamento.
        self.assertAlmostEqualMoney(net, expected_liquido)
        self.assertAlmostEqualMoney(liquido, expected_liquido)
        self.assertGreater(inss_13, 0.0)
        self.assertGreater(irrf_13, 0.0)

    def test_primeira_parcela_proporcional_meio_ano(self):
        """Admitido no meio do ano: 1ª parcela = metade dos avos projetados."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 7, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º Adiantamento - meio de ano",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.structure_13_primeira.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        adiant = self._get_line_total(payslip, "ADIANTAMENTO_13")
        # Admitido jul: 6 avos até 31/12 => 5000 × 6/12 × 0,5 = 1250
        self.assertAlmostEqualMoney(adiant, 1250.00)

    def test_fgts_incide_sobre_13(self):
        """FGTS (8%) incide sobre o 13º bruto na 2ª parcela."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º 2ª Parcela FGTS",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.structure_13_segunda.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        bruto = self._get_line_total(payslip, "DECIMO_TERCEIRO_BRUTO")
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertAlmostEqualMoney(bruto, 5000.00)
        self.assertAlmostEqualMoney(fgts, 400.00)  # 8% de 5000

    def test_decimo_na_rescisao_proporcional(self):
        """13º na rescisão = proporcional aos meses trabalhados no ano."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4800.00, date_start=date(2024, 1, 1))
        rescisao = self.env["hr.payslip"].create(
            {
                "name": "Rescisão - set/2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 9, 1),
                "date_to": date(2024, 9, 30),
                "struct_id": self.structure_rescisao.id,
                "company_id": self.env.company.id,
            }
        )
        rescisao.compute_sheet()
        decimo_rescisao = self._get_line_total(rescisao, "DECIMO_RESCISAO")
        # 9/12 × 4800 = 3600
        self.assertAlmostEqualMoney(decimo_rescisao, 3600.00)
