# Copyright (C) 2025-Today - KMEE (https://www.kmee.com.br).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    summary_line_ids = fields.Many2many(
        "stock.picking.summary.line",
        string="Summary",
        compute="_compute_summary_line_ids",
        store=False,
        help="Moves grouped by product and UoM (computed when form is opened).",
    )
    has_summary = fields.Boolean(
        string="Display Summary",
        compute="_compute_has_summary",
        help="True when moves can be grouped (same product+UoM on multiple lines).",
    )

    @api.depends(
        "move_ids",
        "move_ids.product_id",
        "move_ids.product_uom_qty",
        "move_ids.quantity_done",
        "move_ids.location_id",
        "move_ids.location_dest_id",
    )
    def _compute_summary_line_ids(self):
        SummaryLine = self.env["stock.picking.summary.line"].sudo()
        for picking in self:
            groups = defaultdict(
                lambda: {
                    "product_id": False,
                    "product_uom": False,
                    "product_uom_qty": 0.0,
                    "quantity_done": 0.0,
                    "location_id": False,
                    "location_dest_id": False,
                }
            )
            for move in picking.move_ids_without_package:
                key = (
                    move.product_id.id,
                    move.product_uom.id,
                    move.location_id.id,
                    move.location_dest_id.id,
                )
                g = groups[key]
                g["product_id"] = move.product_id.id
                g["product_uom"] = move.product_uom.id
                g["product_uom_qty"] += move.product_uom_qty
                g["quantity_done"] += move.quantity_done
                g["location_id"] = move.location_id.id
                g["location_dest_id"] = move.location_dest_id.id
            picking.summary_line_ids = (
                SummaryLine.create(
                    [
                        {
                            "product_id": g["product_id"],
                            "product_uom": g["product_uom"],
                            "product_uom_qty": g["product_uom_qty"],
                            "quantity_done": g["quantity_done"],
                            "location_id": g["location_id"],
                            "location_dest_id": g["location_dest_id"],
                        }
                        for g in groups.values()
                    ]
                )
                if groups
                else SummaryLine
            )

    @api.depends(
        "move_ids",
        "move_ids.product_id",
        "move_ids.product_uom",
    )
    def _compute_has_summary(self):
        for picking in self:
            moves = picking.move_ids_without_package
            if not moves:
                picking.has_summary = False
                continue
            keys = {(m.product_id.id, m.product_uom.id) for m in moves}
            picking.has_summary = len(keys) < len(moves)
