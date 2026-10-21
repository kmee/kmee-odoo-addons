# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Relatório Recibo de Férias.

Cobertura:
  - Ação de relatório está registrada
  - Relatório renderiza sem erro
  - Conteúdo HTML contém dados esperados
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestFeriasReport(PayrollCommon):
    """Testes do relatório de recibo de férias."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure_ferias = cls.env.ref("l10n_br_hr_vacation.structure_ferias")

    def _create_ferias_payslip(self):
        """Helper: cria payslip de férias computado."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Férias - {emp.name}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 30),
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_ferias_report_action_exists(self):
        """Ação de relatório de férias está registrada."""
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_recibo_ferias")
        self.assertEqual(report.model, "hr.payslip")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_ferias_report_renders_html(self):
        """Relatório de férias renderiza HTML sem erro."""
        payslip = self._create_ferias_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_recibo_ferias")
        html = self.env["ir.actions.report"]._render_qweb_html(report.id, payslip.ids)
        self.assertTrue(html)
        self.assertTrue(html[0])

    def test_ferias_report_contains_title(self):
        """HTML contém título de recibo de férias."""
        payslip = self._create_ferias_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_recibo_ferias")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, payslip.ids)[0]
            .decode("utf-8")
        )
        self.assertIn("RECIBO DE FÉRIAS", html_content)
        self.assertIn(payslip.employee_id.name, html_content)
