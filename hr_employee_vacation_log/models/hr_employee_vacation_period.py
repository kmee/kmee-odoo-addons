# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeVacationPeriod(models.Model):
    _name = "hr.employee.vacation.period"
    _description = "Employee Vacation Accrual Period"
    _order = "date_from desc, id desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="employee_id.company_id", store=True)
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    date_from = fields.Date(string="Period Start", required=True)
    date_to = fields.Date(
        string="Period End",
        compute="_compute_date_to",
        store=True,
        readonly=False,
    )
    deadline = fields.Date(
        string="Limit to Start",
        compute="_compute_deadline",
        store=True,
        readonly=False,
        help="Latest day to start the vacation so that it ends within the "
        "concession period (11 months after the end of the accrual period).",
    )
    entitled_days = fields.Integer(default=30)
    vacation_ids = fields.One2many(
        comodel_name="hr.employee.vacation",
        inverse_name="period_id",
        string="Vacations",
    )
    taken_days = fields.Integer(compute="_compute_days", store=True)
    remaining_days = fields.Integer(compute="_compute_days", store=True)

    @api.depends("date_from")
    def _compute_date_to(self):
        for period in self:
            if period.date_from:
                period.date_to = period.date_from + relativedelta(years=1, days=-1)

    @api.depends("date_to")
    def _compute_deadline(self):
        for period in self:
            if period.date_to:
                period.deadline = period.date_to + relativedelta(months=11)

    @api.depends("entitled_days", "vacation_ids.days")
    def _compute_days(self):
        for period in self:
            period.taken_days = sum(period.vacation_ids.mapped("days"))
            period.remaining_days = period.entitled_days - period.taken_days

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for period in self:
            if period.date_to and period.date_to < period.date_from:
                raise ValidationError(
                    self.env._("The period end cannot be before the period start.")
                )

    @api.depends("date_from", "date_to")
    def _compute_display_name(self):
        for period in self:
            period.display_name = "{} - {}".format(
                fields.Date.to_string(period.date_from),
                fields.Date.to_string(period.date_to),
            )
