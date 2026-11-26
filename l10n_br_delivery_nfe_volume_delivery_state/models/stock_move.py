# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    delivery_state = fields.Selection(
        selection=[
            ("does_not_apply", "Does Not Apply"),
            ("waiting", "Waiting"),
            ("waiting_delivery", "Available for Delivery"),
            ("partially_delivered", "Partially Delivered"),
            ("delivered", "Delivered"),
        ],
        compute="_compute_delivery_state",
    )
    qty_marked_delivered = fields.Float(
        string="Marked as Delivered",
        compute="_compute_delivery_state",
    )

    @api.depends(
        "location_dest_usage",
        "state",
        "quantity",
        "product_uom_qty",
        "move_line_ids.volume_id.delivery_state",
        "move_line_ids.quantity",
    )
    def _compute_delivery_state(self):
        for move in self:
            move.qty_marked_delivered = 0
            if move.location_dest_usage != "customer":
                move.delivery_state = "does_not_apply"
                continue
            delivered = move.move_line_ids.filtered(
                lambda line: line.volume_id.delivery_state == "delivered"
            )
            move.qty_marked_delivered = sum(delivered.mapped("quantity"))
            reserved = move.quantity if move.state != "done" else 0
            if move.state != "done" and not reserved:
                move.delivery_state = "waiting"
            elif move.qty_marked_delivered < reserved:
                move.delivery_state = "waiting_delivery"
            elif move.qty_marked_delivered < move.product_uom_qty:
                move.delivery_state = "partially_delivered"
            else:
                move.delivery_state = "delivered"
