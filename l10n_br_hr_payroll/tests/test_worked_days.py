# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Dias Trabalhados (worked_days) na Folha.

Cobertura:
  - compute_sheet preenche worked_days quando vazio
  - worked_days existentes não são sobrescritos
  - WORK100 code presente após compute_sheet
  - worked_days acessível nas regras salariais
"""
from .common import PayrollCommon


class TestWorkedDays(PayrollCommon):
    """Testes de preenchimento automático de worked_days."""

    def test_compute_sheet_populates_worked_days(self):
        """compute_sheet deve preencher worked_days_line_ids quando vazio."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        self.assertTrue(
            payslip.worked_days_line_ids,
            "worked_days_line_ids deve ser preenchido após compute_sheet",
        )

    def test_work100_code_present(self):
        """WORK100 deve estar presente nos worked_days."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        codes = payslip.worked_days_line_ids.mapped("code")
        self.assertIn("WORK100", codes)

    def test_worked_days_has_days_and_hours(self):
        """WORK100 deve ter number_of_days e number_of_hours > 0."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        work100 = payslip.worked_days_line_ids.filtered(lambda wd: wd.code == "WORK100")
        self.assertTrue(work100)
        self.assertGreater(work100.number_of_days, 0)
        self.assertGreater(work100.number_of_hours, 0)

    def test_existing_worked_days_not_overwritten(self):
        """worked_days já existentes não devem ser sobrescritos por compute_sheet."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite WD Test",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": "2024-03-01",
                "date_to": "2024-03-31",
                "company_id": self.env.company.id,
            }
        )
        # Manually add a worked_days line
        self.env["hr.payslip.worked_days"].create(
            {
                "name": "Manual WD",
                "code": "MANUAL",
                "number_of_days": 15.0,
                "number_of_hours": 120.0,
                "payslip_id": payslip.id,
                "contract_id": contract.id,
                "sequence": 1,
            }
        )
        payslip.compute_sheet()
        codes = payslip.worked_days_line_ids.mapped("code")
        self.assertIn("MANUAL", codes, "worked_days manual não deve ser removido")
        self.assertNotIn(
            "WORK100", codes, "WORK100 não deve ser adicionado se já há worked_days"
        )
