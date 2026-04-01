# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        self._distribute_shipping_cost()
        return res

    def _is_freight_eligible_line(self, line):
        """Check if a sale order line is eligible for freight distribution.

        In Odoo 18, the product type 'product' (storable) was removed.
        Storable products are now type='consu' with is_storable=True.
        We consider all non-service products as freight-eligible.
        """
        return line.product_id and line.product_id.type != "service"

    def _distribute_shipping_cost(self):
        for order in self:
            if not order.order_line or not order.amount_freight_value:
                continue
            eligible_lines = order.order_line.filtered(
                self._is_freight_eligible_line
            )
            total_wo_delivery = sum(
                line.price_subtotal for line in eligible_lines
            )
            if total_wo_delivery == 0:
                continue
            for line in eligible_lines:
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
