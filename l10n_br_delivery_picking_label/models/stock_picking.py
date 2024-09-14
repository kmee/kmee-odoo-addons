# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    first_volume = fields.Integer()
    last_volume = fields.Integer()
    number_of_volumes = fields.Integer(
        string="Number of Volumes",
        default=0,
        copy=False,
    )

    def action_partially_print(self):
        action = {
            "type": "ir.actions.act_window",
            "name": "Delivery Picking Label Wizard",
            "res_model": "delivery.picking.label.wizard",
            "view_mode": "form",
            "context": "{}",
            "target": "new",
        }
        return action
