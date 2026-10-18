# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrLeaveAbono(models.Model):
    _name = "hr.leave.abono"
    _description = "Hr Leave Abono"

    name = fields.Char(default="Abono Pecuniário", required=True)
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, help="Choose the employee"
    )
    holiday_allocation_id = fields.Many2one(
        "hr.leave.allocation",
        string="Allocation",
        domain="""[
            ('employee_id', '=', employee_id),
            ('hr_holidays_sale_of_days_off', '=', True)]""",
        required=True,
    )
    holiday_allocation_period = fields.Char(
        compute="_compute_holiday_allocation_period"
    )
    date = fields.Date(required=True)
    days_sold = fields.Float(string="Days sold", required=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("paid", "Paid")],
        required=True,
        readonly=True,
        copy=False,
        default="draft",
    )

    @api.onchange("days_sold")
    def _onchange_days_sold(self):
        for abono in self:
            if abono.days_sold:
                number_of_days = abono.holiday_allocation_id.number_of_days_display
                if number_of_days - abono.days_sold < 20:
                    raise ValidationError(
                        _("The requested quantity is not available for sale.")
                    )

    def action_confirm(self):
        for abono in self:
            if not abono.days_sold:
                raise ValidationError(
                    _("The requested number of days sold cannot be 0.")
                )
            number_of_days = abono.holiday_allocation_id.number_of_days_display
            if number_of_days - abono.days_sold < 20:
                raise ValidationError(
                    _("The requested quantity is not available for sale.")
                )
            abono.holiday_allocation_id.sell_days(abono.days_sold)
            abono.state = "paid"

    def _restore_days(self):
        for abono in self:
            if abono.state == "paid" and abono.holiday_allocation_id:
                abono.holiday_allocation_id.number_of_days_sold -= abono.days_sold
                abono.holiday_allocation_id.number_of_days += abono.days_sold

    def unlink(self):
        self._restore_days()
        return super().unlink()

    def action_archive(self):
        self._restore_days()
        return super().action_archive()

    @api.depends("holiday_allocation_id")
    def _compute_holiday_allocation_period(self):
        for record in self:
            record.holiday_allocation_period = False
            if record.holiday_allocation_id:
                date_from = record.holiday_allocation_id.date_from
                date_to = record.holiday_allocation_id.date_to
                record.holiday_allocation_period = ("%s - %s") % (date_from, date_to)
