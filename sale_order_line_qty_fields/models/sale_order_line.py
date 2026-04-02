# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    free_qty = fields.Float(
        related="product_id.free_qty",
        string="Free Qty",
        digits="Product Unit of Measure",
        readonly=True,
    )
