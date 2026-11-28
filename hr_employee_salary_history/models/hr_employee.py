# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    current_salary = fields.Monetary(
        currency_field="currency_id",
        groups="hr.group_hr_user",
        help="Changed through the Adjust Salary button, which keeps the history.",
    )
    salary_history_ids = fields.One2many(
        comodel_name="hr.employee.salary.history",
        inverse_name="employee_id",
        string="Salary History",
        groups="hr.group_hr_user",
    )

    def action_adjust_salary(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Adjust Salary"),
            "res_model": "hr.employee.set.salary",
            "view_mode": "form",
            "target": "new",
            "context": {"default_employee_id": self.id},
        }
