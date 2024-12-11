# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class Hr_attendanceOvertimePaymentWizard(models.TransientModel):

    _name = "hr_attendance.overtime.payment.wizard"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    note = fields.Text(default="Pagamento Horas Extras: ")
    total_overtime = fields.Float(
        related="employee_id.total_overtime", string="Total", required=True
    )
    payment_total = fields.Float(string="Total a ser pago", required=True)

    def doit(self):
        for wizard in self:
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
            .search([("employee_id", "=", wizard.employee_id.id)])
            .ids
        )
        action = {
            "type": "ir.actions.act_window",
            "name": "Employee Overtimes",
            "res_model": "hr.attendance.overtime",
            "domain": [("id", "=", result_ids)],
            "view_mode": "tree",
        }
        return action
