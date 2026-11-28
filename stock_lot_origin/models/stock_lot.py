# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    origin_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Origin Transfer",
        readonly=True,
        copy=False,
        index="btree_not_null",
        help="Transfer of the first movement done with this lot.",
    )
    origin = fields.Char(
        string="Source Document",
        related="origin_picking_id.origin",
        store=True,
    )
    origin_purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Origin Purchase",
        compute="_compute_origin_orders",
        store=True,
        index="btree_not_null",
    )
    origin_sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Origin Sale",
        compute="_compute_origin_orders",
        store=True,
        index="btree_not_null",
    )

    @api.depends("origin_picking_id")
    def _compute_origin_orders(self):
        for lot in self:
            lot.origin_purchase_id = lot.origin_picking_id.purchase_id
            lot.origin_sale_id = lot.origin_picking_id.sale_id
