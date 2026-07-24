# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: Férias CLT.

Cobertura:
  - Dias de férias por faltas (tabela CLT art. 130)
  - Cálculo do valor das férias + adicional 1/3
  - Abono pecuniário (venda de 1/3)
"""
from datetime import date

from odoo.tests import tagged

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestDiasFeriasParFaltas(VacationCommon):
    """Tabela CLT art. 130 — Dias de férias por faltas no período aquisitivo."""

    def _set_faltas(self, employee, faltas):
        """Helper: registra faltas no período aquisitivo."""
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": employee.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date(2023, 3, 1),
                "date_to": date(2024, 2, 29),
            }
        )
        alloc.write({"l10n_br_faltas_periodo_aquisitivo": faltas})
        alloc.action_validate()
        return alloc

    def test_ferias_sem_faltas_30_dias(self):
        """0 faltas → 30 dias de férias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 0)
        self.assertEqual(alloc.number_of_days, 30)

    def test_ferias_5_faltas_30_dias(self):
        """5 faltas → ainda 30 dias (limite máximo da faixa 1)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 5)
        self.assertEqual(alloc.number_of_days, 30)

    def test_ferias_6_faltas_24_dias(self):
        """6 faltas → reduz para 24 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 6)
        self.assertEqual(alloc.number_of_days, 24)

    def test_ferias_14_faltas_24_dias(self):
        """14 faltas → 24 dias (teto da faixa 2)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 14)
        self.assertEqual(alloc.number_of_days, 24)

    def test_ferias_15_faltas_18_dias(self):
        """15 faltas → 18 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 15)
        self.assertEqual(alloc.number_of_days, 18)

    def test_ferias_23_faltas_18_dias(self):
        """23 faltas → 18 dias (teto da faixa 3)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 23)
        self.assertEqual(alloc.number_of_days, 18)

    def test_ferias_24_faltas_12_dias(self):
        """24 faltas → 12 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 24)
        self.assertEqual(alloc.number_of_days, 12)

    def test_ferias_32_faltas_12_dias(self):
        """32 faltas → 12 dias (teto da faixa 4)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 32)
        self.assertEqual(alloc.number_of_days, 12)


@tagged("post_install", "-at_install")
class TestValorFerias(VacationCommon):
    """Testes do cálculo do valor monetário das férias."""

    def test_ferias_30_dias_com_adicional_um_terco(self):
        """30 dias de férias: valor = salário + 1/3 constitucional."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 4, 1),
                "date_to": date(2024, 4, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(ferias, 6000.00)
        self.assertAlmostEqualMoney(adicional, 2000.00)

    def test_adicional_ferias_exatamente_um_terco(self):
        """O adicional de férias deve ser exatamente 1/3 do valor das férias."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4500.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(adicional, ferias / 3)

    def _payslip_ferias(self, emp, contract, abono=False, wage_month=(2024, 5)):
        year, month = wage_month
        return self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(year, month, 1),
                "date_to": date(year, month, 30),
                "struct_id": self.structure_ferias.id,
                "l10n_br_abono_pecuniario": abono,
                "company_id": self.env.company.id,
            }
        )

    def test_abono_pecuniario_ferias_proporcionais(self):
        """Abono: goza 20 dias (férias 20/30), vende 10 dias + 1/3 sobre cada.

        CLT art. 143: ao vender 1/3 (10 dias), o empregado GOZA 20 dias.
        Férias = 20/30 do salário; abono = 10/30 do salário; cada verba
        recebe o seu 1/3 constitucional.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._payslip_ferias(emp, contract, abono=True)
        payslip.compute_sheet()

        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        abono = self._get_line_total(payslip, "ABONO_PECUNIARIO")
        adicional_abono = self._get_line_total(payslip, "ADICIONAL_ABONO")

        self.assertEqual(payslip.l10n_br_dias_ferias_gozadas, 20)
        # Férias gozadas proporcionais: 20/30 × 6000 = 4000 (NÃO paga 30 dias)
        self.assertAlmostEqualMoney(ferias, 4000.00)
        self.assertAlmostEqualMoney(adicional, 4000.00 / 3)
        # Abono: 10 dias × (6000/30) = 2000, com 1/3 constitucional próprio
        self.assertAlmostEqualMoney(abono, 2000.00)
        self.assertAlmostEqualMoney(adicional_abono, 2000.00 / 3)

    def test_abono_isento_inss_irrf(self):
        """Abono e seu 1/3 são indenizatórios: fora do GROSS/base tributável."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        com_abono = self._payslip_ferias(emp, contract, abono=True)
        com_abono.compute_sheet()

        ferias = self._get_line_total(com_abono, "FERIAS")
        adicional = self._get_line_total(com_abono, "ADICIONAL_FERIAS")
        gross = self._get_line_total(com_abono, "GROSS")
        base_irrf = self._get_line_total(com_abono, "BASE_IRRF")
        inss = self._get_line_total(com_abono, "INSS")

        # GROSS = apenas férias gozadas + 1/3 (abono + 1/3 excluídos).
        # Como INSS/IRRF incidem sobre o GROSS, isto prova a isenção do abono.
        self.assertAlmostEqualMoney(gross, ferias + adicional)
        # A base tributável não pode conter o abono (2000) nem seu 1/3.
        self.assertLess(base_irrf, gross)
        self.assertGreater(inss, 0.0)

    def test_fgts_ferias(self):
        """FGTS incide sobre férias gozadas + 1/3 (8%)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._payslip_ferias(emp, contract, abono=False)
        payslip.compute_sheet()
        gross = self._get_line_total(payslip, "GROSS")
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertAlmostEqualMoney(gross, 8000.00)  # 6000 + 1/3
        self.assertAlmostEqualMoney(fgts, 640.00)  # 8% de 8000

    def test_fgts_ferias_exclui_abono(self):
        """FGTS não incide sobre o abono (indenizatório)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._payslip_ferias(emp, contract, abono=True)
        payslip.compute_sheet()
        gross = self._get_line_total(payslip, "GROSS")
        fgts = self._get_line_total(payslip, "FGTS")
        # FGTS = 8% do GROSS (férias gozadas + 1/3), sem o abono.
        self.assertAlmostEqualMoney(fgts, round(gross * 0.08, 2))
