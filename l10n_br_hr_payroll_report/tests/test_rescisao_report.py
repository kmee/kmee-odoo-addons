# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Relatório Termo de Rescisão.

Cobertura:
  - Ação de relatório está registrada
  - Relatório renderiza sem erro
  - Conteúdo HTML contém dados esperados
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestRescisaoReport(PayrollCommon):
    """Testes do relatório de termo de rescisão."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure_rescisao = cls.env.ref("l10n_br_hr_vacation.structure_rescisao")

    def _create_rescisao_payslip(self):
        """Helper: cria payslip de rescisão computado."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Rescisão - {emp.name}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_rescisao.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_rescisao_report_action_exists(self):
        """Ação de relatório de rescisão está registrada."""
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_termo_rescisao")
        self.assertEqual(report.model, "hr.payslip")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_rescisao_report_renders_html(self):
        """Relatório de rescisão renderiza HTML sem erro."""
        payslip = self._create_rescisao_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_termo_rescisao")
        html = self.env["ir.actions.report"]._render_qweb_html(report.id, payslip.ids)
        self.assertTrue(html)
        self.assertTrue(html[0])

    def test_rescisao_report_contains_title(self):
        """HTML contém título do termo de rescisão."""
        payslip = self._create_rescisao_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_termo_rescisao")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, payslip.ids)[0]
            .decode("utf-8")
        )
        self.assertIn("TERMO DE RESCISÃO", html_content.upper())
        self.assertIn(payslip.employee_id.name, html_content)
