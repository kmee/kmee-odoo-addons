# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployeeSetSalary(models.TransientModel):
    _name = "hr.employee.set.salary"
    _description = "Adjust Employee Salary"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="employee_id.company_id.currency_id",
    )
    current_salary = fields.Monetary(
        related="employee_id.current_salary",
        currency_field="currency_id",
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    reason = fields.Char(required=True)
    salary = fields.Monetary(
        string="New Salary",
        currency_field="currency_id",
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()
        self.env["hr.employee.salary.history"].create(
            {
                "employee_id": self.employee_id.id,
                "date": self.date,
                "reason": self.reason,
                "previous_salary": self.employee_id.current_salary,
                "salary": self.salary,
            }
        )
        self.employee_id.current_salary = self.salary
        return {"type": "ir.actions.act_window_close"}
