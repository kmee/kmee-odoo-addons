# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model
    def _update_overtime(self, employee_attendance_dates=None):
        self.env["hr.attendance.overtime"].sudo().search(
            [("attendance_id", "in", self.ids)]
        ).unlink()
        res = super(
            HrAttendance, self.with_context(attendance_ids=self.ids)
        )._update_overtime(employee_attendance_dates)

        overtime_ids = self.env["hr.attendance.overtime"].search(
            [("attendance_id", "in", self.ids)]
        )
        if overtime_ids:
            overtime_ids.sudo().write(
                {"note": _("Automaticamente gerado com base no registro de horas.")}
            )

        return res
