# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrAttendanceOvertime(models.Model):

    _inherit = "hr.attendance.overtime"

    note = fields.Text()

    extra_hours_without_multiplier = fields.Float(
        string="Extra Hours without Multiplier", readonly="1"
    )

    applied_multiplier = fields.Float(default=1.0, readonly="1")

    adjustment_overtime_id = fields.Many2one(
        "hr.attendance.overtime", readonly="1", ondelete="cascade"
    )
    attendance_id = fields.Many2one("hr.attendance", readonly="1", ondelete="cascade")

    overtime_range_id = fields.Many2one(
        "hr.overtime.multiplier.range", string="Multiplier", readonly=True
    )

    def _prepare_overtime_multiplier_ajustements(self):
        for record in self:
            overtime_ranges = self.env[
                "hr.overtime.multiplier.range"
            ]._search_overtime_range(record.date, record.employee_id)
            if not overtime_ranges:
                continue

            if record.duration < 0:
                continue

            duration = record.duration
            duration_real = record.duration_real

            first_range = overtime_ranges[0]
            other_ranges = overtime_ranges[1:]

            if record.duration >= first_range.total_hours:
                record.overtime_range_id = first_range
                record.duration = first_range.total_hours * first_range.multiplier
                record.duration_real = first_range.total_hours * first_range.multiplier
                record.extra_hours_without_multiplier = first_range.total_hours
                record.applied_multiplier = first_range.multiplier
                duration -= first_range.total_hours
                duration_real -= first_range.total_hours
            else:
                record.overtime_range_id = first_range
                record.extra_hours_without_multiplier = record.duration
                record.duration = record.duration * first_range.multiplier
                record.duration_real = record.duration_real * first_range.multiplier
                record.applied_multiplier = first_range.multiplier
                duration -= first_range.total_hours
                duration_real -= first_range.total_hours

            for overtime_range in other_ranges:
                if duration > 0:
                    record.overtime_range_id = overtime_range
                    if duration >= overtime_range.total_hours:
                        duration -= overtime_range.total_hours
                        duration_real -= overtime_range.total_hours
                        self.create(
                            {
                                "adjustment": True,
                                "attendance_id": record.attendance_id.id,
                                "adjustment_overtime_id": record.id,
                                "duration": overtime_range.total
                                * overtime_range.multiplier,
                                "duration_real": overtime_range.total
                                * overtime_range.multiplier,
                                "extra_hours_without_multiplier": overtime_range.total_hours,
                                "applied_multiplier": overtime_range.multiplier,
                                "employee_id": record.employee_id.id,
                                "date": record.date,
                            }
                        )
                    else:
                        self.create(
                            {
                                "adjustment": True,
                                "attendance_id": record.attendance_id.id,
                                "adjustment_overtime_id": record.id,
                                "duration": duration * overtime_range.multiplier,
                                "duration_real": duration * overtime_range.multiplier,
                                "extra_hours_without_multiplier": duration,
                                "applied_multiplier": overtime_range.multiplier,
                                "employee_id": record.employee_id.id,
                                "date": record.date,
                            }
                        )

    @api.model_create_multi
    def create(self, vals_list):
        for attendance in self.env.context.get("attendance_ids", []):
            attendance_id = self.env["hr.attendance"].browse(attendance)
            for vals in vals_list:
                if vals.get("employee_id") == attendance_id.employee_id.id:
                    vals["attendance_id"] = attendance_id.id

        record = super().create(vals_list)
        if not record.filtered("adjustment"):
            record._prepare_overtime_multiplier_ajustements()
        return record

    @api.onchange("duration")
    def onchange_duration(self):
        for record in self:
            if record.duration:
                record.duration_real = record.duration
                record.extra_hours_without_multiplier = record.duration
