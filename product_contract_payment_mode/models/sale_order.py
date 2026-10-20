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

    def action_create_contract(self):
        contracts = super().action_create_contract()
        # contract_payment_mode recomputes the mode from the partner when the
        # contract type is set: keep the payment mode chosen on the order
        for order in self.filtered("is_contract"):
            order.order_line.contract_id.filtered(
                lambda c, o=order: c.payment_mode_id != o.payment_mode_id
            ).payment_mode_id = order.payment_mode_id
        return contracts
