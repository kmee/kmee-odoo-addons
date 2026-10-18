from odoo import models


class HrAttendanceOvertime(models.Model):
    _inherit = "hr.attendance.overtime"

    def action_print_pdf(self):
        return self.env.ref(
            "hr_overtime_report_action_pdf.action_report_overtime"
        ).report_action(self)
