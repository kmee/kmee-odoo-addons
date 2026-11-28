# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployeeSalaryHistory(models.Model):
    _name = "hr.employee.salary.history"
    _description = "Employee Salary History"
    _order = "date desc, id desc"

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
    date = fields.Date(required=True, default=fields.Date.context_today)
    reason = fields.Char(required=True)
    previous_salary = fields.Monetary(currency_field="currency_id")
    salary = fields.Monetary(
        string="New Salary",
        currency_field="currency_id",
        required=True,
    )
    increase_percentage = fields.Float(
        compute="_compute_increase_percentage",
        store=True,
        help="Variation of the new salary over the previous one.",
    )

    @api.depends("previous_salary", "salary")
    def _compute_increase_percentage(self):
        for history in self:
            if history.previous_salary:
                history.increase_percentage = (
                    (history.salary - history.previous_salary)
                    / history.previous_salary
                    * 100
                )
            else:
                history.increase_percentage = 0.0
