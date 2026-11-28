# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    vacation_period_ids = fields.One2many(
        comodel_name="hr.employee.vacation.period",
        inverse_name="employee_id",
        string="Vacation Accrual Periods",
        groups="hr.group_hr_user",
    )
    vacation_ids = fields.One2many(
        comodel_name="hr.employee.vacation",
        inverse_name="employee_id",
        string="Vacations",
        groups="hr.group_hr_user",
    )
