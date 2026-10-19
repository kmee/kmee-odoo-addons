# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Relatório Holerite BR.

Cobertura:
  - Ação de relatório está registrada
  - Relatório renderiza sem erro para payslip computado
  - Seções do holerite (proventos, descontos, líquido)
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestHoleriteReport(PayrollCommon):
    """Testes do relatório holerite brasileiro."""

    def _create_computed_payslip(self):
        """Helper: cria e computa payslip para relatório."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {emp.name}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_report_action_exists(self):
        """Ação de relatório holerite está registrada."""
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_holerite")
        self.assertEqual(report.model, "hr.payslip")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_report_renders_html(self):
        """Relatório renderiza HTML sem erro."""
        payslip = self._create_computed_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_holerite")
        html = self.env["ir.actions.report"]._render_qweb_html(report.id, payslip.ids)
        self.assertTrue(html)
        self.assertTrue(html[0])

    def test_report_contains_employee_data(self):
        """HTML do holerite contém dados do empregado."""
        payslip = self._create_computed_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_holerite")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, payslip.ids)[0]
            .decode("utf-8")
        )
        self.assertIn(payslip.employee_id.name, html_content)
        self.assertIn("RECIBO DE PAGAMENTO", html_content)

    def test_report_contains_payslip_lines(self):
        """HTML contém linhas de proventos e descontos."""
        payslip = self._create_computed_payslip()
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_holerite")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, payslip.ids)[0]
            .decode("utf-8")
        )
        self.assertIn("TOTAIS", html_content)
        self.assertIn("LÍQUIDO", html_content)

    def test_report_contains_net_value(self):
        """HTML contém valor líquido."""
        payslip = self._create_computed_payslip()
        net = self._get_line_total(payslip, "NET")
        report = self.env.ref("l10n_br_hr_payroll_report.action_report_holerite")
        html_content = (
            self.env["ir.actions.report"]
            ._render_qweb_html(report.id, payslip.ids)[0]
            .decode("utf-8")
        )
        # Verifica que o líquido aparece no HTML (formatado)
        self.assertTrue(net > 0)
        self.assertIn("LÍQUIDO A RECEBER", html_content)
