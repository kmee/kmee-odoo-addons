# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeVacation(models.Model):
    _name = "hr.employee.vacation"
    _description = "Employee Vacation"
    _order = "date_from desc, id desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    period_id = fields.Many2one(
        comodel_name="hr.employee.vacation.period",
        string="Accrual Period",
        domain="[('employee_id', '=', employee_id)]",
        ondelete="restrict",
    )
    date_from = fields.Date(string="Start", required=True)
    date_to = fields.Date(string="End", required=True)
    days = fields.Integer(compute="_compute_days", store=True)
    cash_bonus = fields.Boolean(
        help="Part of the vacation is sold (abono pecuniário).",
    )
    thirteenth_advance = fields.Boolean(
        string="13th Salary Advance",
        help="The first installment of the 13th salary is paid with this vacation.",
    )
    note = fields.Char()

    @api.depends("date_from", "date_to")
    def _compute_days(self):
        for vacation in self:
            if vacation.date_from and vacation.date_to:
                vacation.days = (vacation.date_to - vacation.date_from).days + 1
            else:
                vacation.days = 0

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for vacation in self:
            if vacation.date_to < vacation.date_from:
                raise ValidationError(
                    self.env._("The vacation end cannot be before its start.")
                )

    @api.constrains("employee_id", "period_id")
    def _check_period_employee(self):
        for vacation in self:
            if vacation.period_id and vacation.period_id.employee_id != (
                vacation.employee_id
            ):
                raise ValidationError(
                    self.env._("The accrual period must belong to the same employee.")
                )
