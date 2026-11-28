# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPickingVol(models.Model):
    _inherit = "stock.picking.vol"

    delivery_state = fields.Selection(
        selection=[("waiting", "Waiting"), ("delivered", "Delivered")],
        default="waiting",
    )
    delivery_date = fields.Date(string="Departure Date")
    color = fields.Integer(compute="_compute_color")

    @api.depends("delivery_state")
    def _compute_color(self):
        for vol in self:
            vol.color = 10 if vol.delivery_state == "delivered" else 3

    def button_change_delivery_state(self):
        for vol in self:
            if vol.delivery_state == "waiting":
                vol.write(
                    {
                        "delivery_state": "delivered",
                        "delivery_date": fields.Date.context_today(vol),
                    }
                )
            else:
                vol.write({"delivery_state": "waiting", "delivery_date": False})
