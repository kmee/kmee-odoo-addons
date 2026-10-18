# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeaveType(models.Model):

    _inherit = "hr.leave.type"

    hr_holidays_sale_of_days_off = fields.Boolean()
