# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import _, fields, models


class HrEmployee(models.Model):

    _inherit = "hr.employee"

    days_off_sold_display = fields.Char(compute="_compute_days_off_sold_display")

    def action_sale_of_days_off(self):
        default_allocation_id = self._get_default_hr_leave_allocation_id()["id"]
        return {
            "name": _("Holiday Sales"),
            "view_mode": "tree,form",
            "res_model": "hr.leave.abono",
            "target": "current",
            "type": "ir.actions.act_window",
            "context": {
                "default_employee_id": self.id,
                "default_holiday_allocation_id": default_allocation_id,
                "default_date": date.today(),
                "create_name_button": "Register Vacation Sale”",
            },
            "domain": [("employee_id", "=", self.id)],
        }

    def _get_default_hr_leave_allocation_id(self):
        today = date.today()
        allocation = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", self.id),
                ("date_from", "<", today),
                ("date_to", ">", today),
            ],
            limit=1,
        )
        return {"id": allocation.id, "allocation_id": allocation}

    def _compute_days_off_sold_display(self):
        self.ensure_one()
        current_allocation = self._get_default_hr_leave_allocation_id()["allocation_id"]
        value = current_allocation.number_of_days_sold
        self.days_off_sold_display = int(value) if value == int(value) else value
