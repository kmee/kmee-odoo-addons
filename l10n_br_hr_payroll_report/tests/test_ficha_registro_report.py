# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Relatório Ficha de Registro de Empregado.

Cobertura:
  - Ação de relatório está registrada
  - Relatório renderiza sem erro
  - Conteúdo HTML contém dados do empregado
"""
from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestFichaRegistroReport(PayrollCommon):
    """Testes do relatório de ficha de registro."""

    def test_ficha_report_action_exists(self):
        """Ação de relatório de ficha de registro está registrada."""
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_ficha_registro")
        self.assertEqual(report.model, "hr.employee")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_ficha_report_renders_html(self):
        """Relatório de ficha de registro renderiza HTML sem erro."""
        emp = self._create_employee()
        self._create_contract(emp, wage=5000.00)
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_ficha_registro")
        html = self.env["ir.actions.report"]._render_qweb_html(report.id, emp.ids)
        self.assertTrue(html)
        self.assertTrue(html[0])

    def test_ficha_report_contains_employee_data(self):
        """HTML contém dados do empregado."""
        emp = self._create_employee()
        self._create_contract(emp, wage=5000.00)
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_ficha_registro")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, emp.ids)[0]
            .decode("utf-8")
        )
        self.assertIn("FICHA DE REGISTRO", html_content)
        self.assertIn(emp.name, html_content)
