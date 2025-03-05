# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.onchange("payment_mode_id")
    def _onchange_payment_mode_id(self):
        for rec in self.filtered("is_contract"):
            line_to_change_payment_mode_id = rec.order_line.filtered(
                lambda r: r.contract_id and r.product_id.is_contract
            )

            for order_line in line_to_change_payment_mode_id:
                order_line.contract_id.write({"payment_mode_id": self.payment_mode_id})

    def _prepare_contract_value(self, contract_template):
        self.ensure_one()
        res = super()._prepare_contract_value(contract_template)
        res["payment_mode_id"] = self.payment_mode_id.id
        return res
