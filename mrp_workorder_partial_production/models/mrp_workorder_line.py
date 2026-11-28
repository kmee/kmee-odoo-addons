# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MrpWorkorderLine(models.Model):
    _name = "mrp.workorder.line"
    _description = "Work Order Component Consumption"
    _rec_name = "product_id"

    workorder_id = fields.Many2one(
        "mrp.workorder", required=True, index=True, ondelete="cascade"
    )
    move_id = fields.Many2one("stock.move", required=True, ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", related="move_id.product_id", store=True
    )
    product_uom_id = fields.Many2one("uom.uom", related="move_id.product_uom")
    qty_done = fields.Float(
        string="Consumed",
        digits="Product Unit of Measure",
        help="Component quantity consumed by the quantity recorded in the "
        "work order. It is posted to the manufacturing order on launch.",
    )
