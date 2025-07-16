# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import _, api, fields, models


class HrLeaveAllocation(models.Model):

    _inherit = "hr.leave.allocation"

    number_of_days_sold = fields.Float(string="Days sold", help="Days sold", default=0)
    days_off_sold_display = fields.Char(compute="_compute_days_off_sold_display")

    def sell_days(self, days):
        self.ensure_one()
        self.number_of_days_sold += days
        self.number_of_days -= days

    def action_sale_of_days_off(self):
        return {
            "name": _("Holiday Sales"),
            "view_mode": "tree,form",
            "res_model": "hr.leave.abono",
            "target": "current",
            "type": "ir.actions.act_window",
            "context": {
                "default_employee_id": self.employee_id.id,
                "default_holiday_allocation_id": self.id,
                "default_date": date.today(),
                "create_name_button": "Register Vacation Sale”",
            },
            "domain": [
                ("employee_id", "=", self.employee_id.id),
                ("holiday_allocation_id", "=", self.id),
            ],
        }

    @api.depends("number_of_days_sold")
    def _compute_days_off_sold_display(self):
        self.ensure_one()
        value = self.number_of_days_sold
        self.days_off_sold_display = int(value) if value == int(value) else value
