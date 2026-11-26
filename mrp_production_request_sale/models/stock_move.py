# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    created_after_sale_order_confirmed = fields.Boolean(
        help="The move comes from a sale order line added after the order was "
        "confirmed.",
        copy=False,
    )
