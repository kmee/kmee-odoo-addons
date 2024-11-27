# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrAttendanceOvertime(models.Model):

    _inherit = "hr.attendance.overtime"

    extra_hours_withou_multiplier = fields.Float(
        string="Extra Hours without Multiplier"
    )

    applied_multiplier = fields.Float(default=1.0)
