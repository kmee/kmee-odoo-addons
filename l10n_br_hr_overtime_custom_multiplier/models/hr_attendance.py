# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model
    def _update_overtime(self, employee_attendance_dates=None):
        self.env["hr.attendance.overtime"].search(
            [("attendance_id", "in", self.ids)]
        ).unlink()
        res = super(
            HrAttendance, self.with_context(attendance_ids=self.ids)
        )._update_overtime(employee_attendance_dates)

        overtime_ids = self.env["hr.attendance.overtime"].search(
            [("attendance_id", "in", self.ids)]
        )
        if overtime_ids:
            overtime_ids.write(
                {"note": "Automaticamente gerado com base no registro de horas."}
            )  # noqa

        return res


#     def get_overtime_multiplier(date_time,
# original_overtime, is_holiday=False, employee_id=None):
#         # Check if there is an exception
# for this employee on this date
#         exception = self.env['hr.attendance.exception'].search([
#             ('employee_id', '=', employee_id),
#             ('date', '=', date_time.date())
#         ], limit=1)

#         if exception:
#             day_of_week = exception.day_of_week_override
#         else:
#             day_of_week = 'holiday' if is_holiday else (
#                 'monday' if date_time.weekday() == 0 else
#                 'tuesday' if date_time.weekday() == 1 else
#                 'wednesday' if date_time.weekday() == 2 else
#                 'thursday' if date_time.weekday() == 3 else
#                 'friday' if date_time.weekday() == 4 else
#                 'saturday' if date_time.weekday() == 5 else
#                 'sunday' if date_time.weekday() == 6 else 'weekday')

#         # Search for applicable multiplier range
#         applicable_range = self.env['hr.overtime.multiplier.range'].search([
#             ('overtime_from', '<=', original_overtime),
#             ('overtime_to', '>', original_overtime),
#             # "|",

#             # ('monday', '=', day_of_week == 'monday'),
#             # ('tuesday', '=', day_of_week == 'tuesday'),
#             # ('wednesday', '=', day_of_week == 'wednesday'),
#             # ('thursday', '=', day_of_week == 'thursday'),
#             # ('friday', '=', day_of_week == 'friday'),
#             # ('saturday', '=', day_of_week == 'saturday'),
#             # ('sunday', '=', day_of_week == 'sunday'),
#             # ('holiday', '=', day_of_week == 'holiday'),
#         ], limit=1)

#         return applicable_range.multiplier if applicable_range else 1.0

#     if employee_attendance_dates is None:
#         employee_attendance_dates = self._get_attendances_dates()

#     self.env["hr.attendance.overtime"].flush_model(["duration", "duration_real"])

#     for emp, attendance_dates in employee_attendance_dates.items():
#         for day_data in attendance_dates:
#             attendance_date = day_data[1]
#             overtime = self.env["hr.attendance.overtime"].search(
#                 [
#                     ("employee_id", "=", emp.id),
#                     ("date", "=", attendance_date),
#                     ("adjustment", "=", False),
#                 ]
#             )

#             # Convert attendance_date to a datetime object if it is a date object
#             if isinstance(attendance_date, date)
# and not isinstance(attendance_date, datetime):
#                 attendance_date = datetime.combine(attendance_date, datetime.min.time())

#             is_holiday = emp.resource_calendar_id.data_eh_feriado(attendance_date)

#             if overtime:
#                 for overtime_record in overtime:
#                     overtime_multiplier = get_overtime_multiplier(
#                         attendance_date, overtime_record.duration, is_holiday, emp.id
#                     )

#                     overtime_record.write(
#                         {
#                             "duration":
#   overtime_record.duration * overtime_multiplier,
#                             "duration_real":
# overtime_record.duration_real * overtime_multiplier,
#                             "extra_hours_withou_multiplier":
# overtime_record.duration,
#                             "applied_multiplier": overtime_multiplier,
#                         }
#                     )

#     return res
