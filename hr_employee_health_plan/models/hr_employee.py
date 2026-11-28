# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    health_plan_ids = fields.One2many(
        comodel_name="hr.employee.health.plan",
        inverse_name="employee_id",
        string="Health and Dental Plans",
        groups="hr.group_hr_user",
    )
