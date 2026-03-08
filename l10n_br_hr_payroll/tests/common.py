# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Classe base com fixtures compartilhadas por todos os testes ORM de folha.
"""
from datetime import date

from odoo.tests.common import TransactionCase


class PayrollCommon(TransactionCase):
    """Classe base com fixtures para testes de folha de pagamento BR."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure_clt = cls.env.ref("l10n_br_hr_payroll.structure_clt")
        cls.structure_estatuto = cls.env.ref("l10n_br_hr_payroll.structure_estatuto")

    def _create_employee(self, name="Funcionário Teste", tipo_contrato="clt"):
        """Helper: cria funcionário com tipo de contrato."""
        return self.env["hr.employee"].create(
            {
                "name": name,
                "l10n_br_tipo_contrato": tipo_contrato,
                "company_id": self.env.company.id,
            }
        )

    def _create_contract(self, employee, wage=5000.0, structure=None, date_start=None):
        """Helper: cria contrato de trabalho com estrutura salarial."""
        return self.env["hr.contract"].create(
            {
                "name": f"Contrato - {employee.name}",
                "employee_id": employee.id,
                "wage": wage,
                "date_start": date_start or date(2024, 1, 1),
                "state": "open",
                "struct_id": (structure or self.structure_clt).id,
                "company_id": self.env.company.id,
            }
        )

    def _create_payslip(self, employee, contract, date_from=None, date_to=None):
        """Helper: cria e calcula contracheque."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date_from or date(2024, 3, 1),
                "date_to": date_to or date(2024, 3, 31),
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def _get_line_total(self, payslip, code):
        """Helper: retorna o total de uma linha pelo código da salary rule."""
        lines = payslip.line_ids.filtered(lambda line: line.code == code)
        if not lines:
            return 0.0
        return sum(lines.mapped("total"))

    def assertAlmostEqualMoney(self, first, second, msg=None, places=2):
        """Comparação monetária com tolerância de centavos."""
        self.assertAlmostEqual(first, second, places=places, msg=msg)
