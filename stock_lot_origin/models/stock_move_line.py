# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    lot_origin_picking_id = fields.Many2one(
        related="lot_id.origin_picking_id",
        string="Lot Origin Transfer",
    )
    lot_origin_purchase_id = fields.Many2one(
        related="lot_id.origin_purchase_id",
        string="Lot Origin Purchase",
    )
    lot_origin_sale_id = fields.Many2one(
        related="lot_id.origin_sale_id",
        string="Lot Origin Sale",
    )

    def _set_lot_origin(self):
        """The origin of a lot is the transfer of its first done movement."""
        lots = self.exists().lot_id.filtered(lambda lot: not lot.origin_picking_id)
        for lot in lots:
            first_line = self.search(
                [("lot_id", "=", lot.id), ("state", "=", "done")],
                order="date, id",
                limit=1,
            )
            if first_line.picking_id:
                lot.origin_picking_id = first_line.picking_id
