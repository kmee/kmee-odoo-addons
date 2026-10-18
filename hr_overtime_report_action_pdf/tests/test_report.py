# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOvertimeReport(TransactionCase):
    def test_report_renders_employee(self):
        employee = self.env["hr.employee"].create({"name": "Overtime Tester"})
        overtime = self.env["hr.attendance.overtime"].create(
            {"employee_id": employee.id, "duration": 2.0}
        )
        report = self.env.ref("hr_overtime_report_action_pdf.action_report_overtime")
        html, _report_type = report._render_qweb_html(report.report_name, overtime.ids)
        self.assertIn("Overtime Tester", html.decode())

    def test_action_print_pdf(self):
        employee = self.env["hr.employee"].create({"name": "Overtime Tester"})
        overtime = self.env["hr.attendance.overtime"].create(
            {"employee_id": employee.id, "duration": 1.0}
        )
        action = overtime.action_print_pdf()
        self.assertTrue(action.get("type"))
