# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Hr_attendanceOvertimePaymentWizard(models.TransientModel):
    _name = "hr_attendance.overtime.payment.wizard"
    _description = "Overtime Payment Wizard"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    note = fields.Text(default="Pagamento Horas Extras: ")
    total_overtime = fields.Float(string="Total", compute="_compute_total_overtime")
    payment_total = fields.Float(string="Total a ser pago", required=True)

    @api.depends("employee_id")
    def _compute_total_overtime(self):
        # The core total_overtime (18.0) only counts approved attendance hours
        # plus adjustments, ignoring the multiplier applied by this module.
        for wizard in self:
            wizard.total_overtime = sum(
                wizard.employee_id.sudo().overtime_ids.mapped("duration")
            )

    def doit(self):
        for wizard in self:
            if wizard.payment_total <= 0:
                raise UserError(_("The payment total must be greater than zero."))
            if wizard.payment_total > wizard.total_overtime:
                raise UserError(
                    _("The payment total cannot be greater than the total overtime.")
                )
            self.env["hr.attendance.overtime"].create(
                {
                    "date": wizard.date,
                    "employee_id": wizard.employee_id.id,
                    "duration": wizard.payment_total * -1,
                    "duration_real": wizard.payment_total * -1,
                    "adjustment": True,
                    "note": wizard.note,
                }
            )
        result_ids = (
            self.env["hr.attendance.overtime"]
            .search([("employee_id", "in", self.employee_id.ids)])
            .ids
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("Employee Overtimes"),
            "res_model": "hr.attendance.overtime",
            "domain": [("id", "in", result_ids)],
            "view_mode": "list",
        }
        return action
