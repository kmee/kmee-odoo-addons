# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class HrEmployeeVacationScheduleWizard(models.TransientModel):
    _name = "hr.employee.vacation.schedule.wizard"
    _description = "Vacation Schedule Report Wizard"

    department_ids = fields.Many2many(
        comodel_name="hr.department",
        string="Departments",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
    )
    only_with_balance = fields.Boolean(
        string="Only Periods With Remaining Days",
        default=True,
    )

    def _get_periods(self):
        domain = []
        if self.employee_ids:
            domain.append(("employee_id", "in", self.employee_ids.ids))
        if self.department_ids:
            domain.append(("department_id", "in", self.department_ids.ids))
        if self.only_with_balance:
            domain.append(("remaining_days", ">", 0))
        return self.env["hr.employee.vacation.period"].search(
            domain, order="deadline, employee_id"
        )

    def action_print(self):
        self.ensure_one()
        periods = self._get_periods()
        if not periods:
            raise UserError(self.env._("There are no vacation periods to print."))
        return self.env.ref(
            "hr_employee_vacation_log.action_report_vacation_schedule"
        ).report_action(periods)
