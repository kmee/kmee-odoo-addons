# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime

from odoo import api, fields, models


class HrOvertimeMultiplierRange(models.Model):
    _name = "hr.overtime.multiplier.range"
    _description = "Overtime Multiplier Range"
    _order = "overtime_from"

    @api.depends("overtime_from", "overtime_to")
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = record.overtime_to - record.overtime_from

    name = fields.Char(required=True)

    monday = fields.Boolean(string="2ª", default=False)
    tuesday = fields.Boolean(string="3ª", default=False)
    wednesday = fields.Boolean(string="4ª", default=False)
    thursday = fields.Boolean(string="5ª", default=False)
    friday = fields.Boolean(string="6ª", default=False)
    saturday = fields.Boolean(string="Sabado", default=False)
    sunday = fields.Boolean(string="Domingo", default=False)
    holiday = fields.Boolean(string="Feriado", default=False)

    overtime_from = fields.Float(string="From (hours)", required=True)
    overtime_to = fields.Float(string="To (hours)", required=True)
    multiplier = fields.Float(required=True)

    total_hours = fields.Float(compute="_compute_total_hours", store=True)

    @api.model
    def _search_overtime_range(self, attendance_date, employee_id=None):
        if not attendance_date:
            return self

        exception_id = self.env["hr.attendance.exception"]

        day_name = fields.Date.from_string(attendance_date).strftime("%A").lower()
        domain = []

        if employee_id:
            exception_id = exception_id.search(
                [("employee_id", "=", employee_id.id), ("date", "=", attendance_date)],
                limit=1,
            )

            if exception_id:
                domain.append((exception_id.day_of_week_override, "=", True))

        if not exception_id:

            if day_name == "monday":
                domain.append(("monday", "=", True))
            elif day_name == "tuesday":
                domain.append(("tuesday", "=", True))
            elif day_name == "wednesday":
                domain.append(("wednesday", "=", True))
            elif day_name == "thursday":
                domain.append(("thursday", "=", True))
            elif day_name == "friday":
                domain.append(("friday", "=", True))
            elif day_name == "saturday":
                domain.append(("saturday", "=", True))
            elif day_name == "sunday":
                domain.append(("sunday", "=", True))

            # Convert attendance_date to a datetime object if it is a date object
            if isinstance(attendance_date, date) and not isinstance(
                attendance_date, datetime
            ):
                attendance_date = datetime.combine(attendance_date, datetime.min.time())

            if employee_id and employee_id.resource_calendar_id.data_eh_feriado(
                attendance_date
            ):
                domain.append(("holiday", "=", True))

        overtime_ranges = self.search(domain)
        return overtime_ranges

    # @api.constrains(
    #     'monday', 'tuesday', 'wednesday',
    #     'thursday', 'friday', 'saturday',
    #     'sunday', 'holidays', 'overtime_from', 'overtime_to')
    # def _check_overlap(self):
    #     for record in self:
    #         overlapping_ranges = self.search_count([
    #             ('id', '!=', record.id),
    #             ('overtime_from', '<=', record.overtime_to),
    #             ('overtime_to', '>=', record.overtime_from),
    #             '|',
    #             ('monday', '=', True if record.monday else False),
    #             ('tuesday', '=', True if record.tuesday else False),
    #             '|',
    #             ('wednesday', '=', True if record.wednesday else False),
    #             '|',
    #             ('thursday', '=', True if record.thursday else False),
    #             '|',
    #             ('friday', '=', True if record.friday else False),
    #             '|',
    #             ('saturday', '=', True if record.saturday else False),
    #             '|',
    #             ('sunday', '=', True if record.sunday else False),
    #             '|',
    #             ('holidays', '=', True if record.holidays else False),
    #         ])
    #         if overlapping_ranges:
    #             raise ValidationError("Overlapping overtime
    # ranges are not allowed for the same day.")
