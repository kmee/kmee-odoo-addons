# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class HrAttendance(models.Model):

    _inherit = "hr.attendance"

    @api.model
    def _update_overtime(self, employee_attendance_dates=None):
        res = super(HrAttendance, self)._update_overtime(employee_attendance_dates)

        def get_overtime_multiplier_and_bank_time(date_time, original_overtime, is_holiday=False):

            config_params = self.env['ir.config_parameter'].sudo()

            # Get the day of the week (0=Monday, 6=Sunday)
            day_of_week = date_time.weekday()

            # Check if it is a holiday
            if is_holiday:
                return float(config_params.get_param('sunday_holidays_overtime_multiplier', 1))

            # Saturdays (day 5)
            if day_of_week == 5:
                return float(config_params.get_param('saturday_overtime_multiplier', 1))

            # Sundays (day 6)
            if day_of_week == 6:
                return float(config_params.get_param('sunday_holidays_overtime_multiplier', 1))

            # For weekdays (Monday to Friday)
            if original_overtime < 2:  # Less than 2 hours of overtime
                return float(config_params.get_param('business_days_under_2_hours_overtime_multiplier', 1))
            else:  # More than 2 hours of overtime
                return float(config_params.get_param('business_days_over_2_hours_overtime_multiplier', 1))

        if employee_attendance_dates is None:
            employee_attendance_dates = self._get_attendances_dates()

        self.env['hr.attendance.overtime'].flush_model(["duration", "duration_real"])

        for emp, attendance_dates in employee_attendance_dates.items():
            for day_data in attendance_dates:
                attendance_date = day_data[1]
                overtime = self.env['hr.attendance.overtime'].search([
                    ('employee_id', '=', emp.id),
                    ('date', '=', attendance_date),
                    ('adjustment', '=', False),
                ])

                is_holiday = emp.resource_calendar_id.data_eh_feriado(attendance_date)

                if overtime:
                    for overtime_record in overtime:
                        overtime_multiplier = get_overtime_multiplier_and_bank_time(
                            attendance_date,
                            overtime_record.duration,
                            is_holiday
                        )

                        overtime_record.write({
                            'duration': overtime_record.duration * overtime_multiplier,
                            'duration_real': overtime_record.duration_real * overtime_multiplier,
                            'extra_hours_withou_multiplier': overtime_record.duration,
                            'applied_multiplier': overtime_multiplier
                        })

        return res
