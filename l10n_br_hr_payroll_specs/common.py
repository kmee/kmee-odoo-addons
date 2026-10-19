# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
Classe base com fixtures compartilhadas por todos os testes de folha.
Herdar desta classe nos módulos de teste específicos.
"""
from datetime import date

from odoo.tests.common import TransactionCase


class PayrollCommon(TransactionCase):
    """Classe base com fixtures para testes de folha de pagamento BR."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Empresa ──────────────────────────────────────────────
        cls.company = cls.env["res.company"].create(
            {
                "name": "ABGF - Associação dos Funcionários Test",
                "vat": "00.000.000/0001-00",
                "country_id": cls.env.ref("base.br").id,
            }
        )

        # ── Estruturas Salariais ──────────────────────────────────
        cls.structure_clt = cls.env.ref(
            "l10n_br_hr_payroll.structure_clt", raise_if_not_found=False
        ) or cls.env["hr.payroll.structure"].create(
            {
                "name": "CLT",
                "code": "CLT",
                "company_id": cls.company.id,
            }
        )

        cls.structure_estatuto = cls.env.ref(
            "l10n_br_hr_payroll.structure_estatuto", raise_if_not_found=False
        ) or cls.env["hr.payroll.structure"].create(
            {
                "name": "ESTATUTO ABGF",
                "code": "ESTATUTO_ABGF",
                "company_id": cls.company.id,
            }
        )

        # ── Departamento ─────────────────────────────────────────
        cls.department = cls.env["hr.department"].create(
            {
                "name": "TI",
                "company_id": cls.company.id,
            }
        )

        # ── Cargo ────────────────────────────────────────────────
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Analista de Sistemas",
                "department_id": cls.department.id,
                "company_id": cls.company.id,
            }
        )

    def _create_employee(
        self,
        name="Funcionário Teste",
        cpf="123.456.789-09",
        pis="123.45678.90-1",
        tipo_contrato="clt",
        regime_previdenciario="inss",
    ):
        """Helper: cria funcionário com dados brasileiros."""
        return self.env["hr.employee"].create(
            {
                "name": name,
                "l10n_br_cpf": cpf,
                "l10n_br_pis": pis,
                "l10n_br_tipo_contrato": tipo_contrato,
                "l10n_br_regime_previdenciario": regime_previdenciario,
                "department_id": self.department.id,
                "job_id": self.job.id,
                "company_id": self.company.id,
            }
        )

    def _create_contract(
        self,
        employee,
        wage=5000.0,
        date_start=None,
        date_end=False,
        structure=None,
    ):
        """Helper: cria contrato de trabalho."""
        return self.env["hr.contract"].create(
            {
                "name": f"Contrato - {employee.name}",
                "employee_id": employee.id,
                "wage": wage,
                "date_start": date_start or date(2024, 1, 1),
                "date_end": date_end,
                "state": "open",
                "struct_id": (structure or self.structure_clt).id,
                "company_id": self.company.id,
            }
        )

    def _create_payslip(self, employee, contract, date_from=None, date_to=None):
        """Helper: cria e calcula contracheque."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "date_from": date_from or date(2024, 3, 1),
                "date_to": date_to or date(2024, 3, 31),
                "company_id": self.company.id,
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
