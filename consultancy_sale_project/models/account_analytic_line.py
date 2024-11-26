# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticLine(models.Model):

    _inherit = "account.analytic.line"

    @api.onchange("contract_line_id")
    def onchange_contract_line_id(self):
        if self.contract_line_id and self.contract_line_id.sale_order_line_id:
            self.so_line = self.contract_line_id.sale_order_line_id

    def _hourly_cost(self):
        mapping_entries = self.project_id.sale_line_employee_ids.filtered(
            lambda r: r.employee_id == self.employee_id
        )
        if mapping_entries:
            total_cost = sum(entry.cost for entry in mapping_entries)
            return total_cost / len(mapping_entries)
        return 0.0
