# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrAttendanceException(models.Model):
    _name = "hr.attendance.exception"
    _description = "Attendance Exception"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    date = fields.Date(required=True)
    day_of_week_override = fields.Selection(
        [
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
            ("holiday", "Holiday"),
        ],
        string="Override Day of the Week",
        required=True,
    )

    @api.constrains("employee_id", "date")
    def _check_duplicate_exception(self):
        for record in self:
            duplicate_exception = self.search(
                [
                    ("employee_id", "=", record.employee_id.id),
                    ("date", "=", record.date),
                    ("id", "!=", record.id),
                ]
            )
            if duplicate_exception:
                raise ValidationError(
                    _("An exception already exists for this employee on this date.")
                )
