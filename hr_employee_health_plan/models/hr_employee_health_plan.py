# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeHealthPlan(models.Model):
    _name = "hr.employee.health.plan"
    _description = "Employee Health Plan"
    _order = "date_start desc, id desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="employee_id.company_id.currency_id",
    )
    plan_type = fields.Selection(
        selection=[("health", "Health"), ("dental", "Dental")],
        required=True,
        default="health",
    )
    operator = fields.Char(help="Company that provides the plan.")
    date_start = fields.Date(string="Start")
    date_end = fields.Date(string="End")
    amount = fields.Monetary(
        string="Amount Paid",
        currency_field="currency_id",
    )
    description = fields.Char()

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for plan in self:
            if plan.date_start and plan.date_end and plan.date_end < plan.date_start:
                raise ValidationError(
                    self.env._("The plan end cannot be before its start.")
                )
