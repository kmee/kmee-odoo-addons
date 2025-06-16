# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    use_period_quantity = fields.Boolean(
        related="product_id.uom_id.use_period_quantity"
    )

    def _prepare_sale_order_line_values(self):
        res = super()._prepare_sale_order_line_values()
        fields_map = {
            "period_qty": self.period_qty,
            "period_count": self.period_count,
            "date_start": self.date_start,
            "date_end": self.date_end,
        }
        res.update(fields_map)
        return res
