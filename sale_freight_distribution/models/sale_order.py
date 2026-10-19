# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        self._distribute_shipping_cost()
        return res

    def _distribute_shipping_cost(self):
        for order in self:
            if not order.order_line or not order.amount_freight_value:
                continue
            total_wo_delivery = sum(
                line.price_subtotal
                for line in order.order_line
                if line.product_id.type == "product"
            )
            if total_wo_delivery == 0:
                continue
            for line in order.order_line:
                if line.product_id.type != "product":
                    continue
                proportion = line.price_subtotal / total_wo_delivery
                line.freight_value = (
                    order.amount_freight_value * proportion / line.product_uom_qty
                )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def unlink(self):
        orders = self.mapped("order_id")
        res = super().unlink()
        orders._distribute_shipping_cost()
        return res
