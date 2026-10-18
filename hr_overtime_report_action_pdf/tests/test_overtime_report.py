# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOvertimeReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Overtime Employee"})
        cls.overtime = cls.env["hr.attendance.overtime"].create(
            {
                "employee_id": cls.employee.id,
                "date": "2026-01-10",
                "duration": 2.0,
            }
        )
        cls.report = cls.env.ref("hr_overtime_report_action_pdf.action_report_overtime")

    def test_action_print_pdf_returns_report_action(self):
        action = self.overtime.with_context(discard_logo_check=True).action_print_pdf()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], self.report.report_name)
        self.assertEqual(action["context"]["active_ids"], self.overtime.ids)

    def test_report_html_contains_employee(self):
        html, _fmt = self.report._render_qweb_html(self.report.id, self.overtime.ids)
        self.assertIn("Overtime Employee", html.decode())
