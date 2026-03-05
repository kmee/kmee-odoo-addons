# Copyright (C) 2025-Today - KMEE (https://www.kmee.com.br).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPickingSummaryLine(models.TransientModel):
    _name = "stock.picking.summary.line"
    _description = "Stock Picking Operations Summary Line"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfer",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )
    product_uom = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
    )
    product_uom_qty = fields.Float(
        string="Demand",
        digits="Product Unit of Measure",
    )
    quantity_done = fields.Float(
        string="Done",
        digits="Product Unit of Measure",
    )
