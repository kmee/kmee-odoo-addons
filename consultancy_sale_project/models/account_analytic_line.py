# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticLine(models.Model):

    _inherit = "account.analytic.line"

    @api.onchange("contract_line_id")
    def onchange_contract_line_id(self):
        if self.contract_line_id and self.contract_line_id.sale_order_line_id:
            self.so_line = self.contract_line_id.sale_order_line_id
