# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):

    _inherit = "hr.employee"

    plan_allocation_ids = fields.Many2many(
        "hr.leave.allocation",
        relation="hr_allocation_employee_rel",
        column1="employee_id",
        column2="allocation_id",
    )
