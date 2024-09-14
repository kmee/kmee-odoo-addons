# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class DeliveryPickingLabelWizard(models.TransientModel):

    _name = "delivery.picking.label.wizard"

    first_volume = fields.Integer(string="First Volume", default=1)
    last_volume = fields.Integer(string="Last Volume")
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        default=lambda self: self.env.context.get("active_id"),
    )

    def print(self):
        picking = self.env["stock.picking"].browse(self.env.context.get("active_id"))
        vals = {
            "first_volume": self.first_volume,
            "last_volume": self.last_volume,
        }
        picking.write(vals)
        return self.env.ref(
            "l10n_br_delivery_picking_label.report_delivery_picking_label"
        ).report_action([])

    @api.onchange("picking_id")
    def _onchange_picking_id(self):
        self.last_volume = self.picking_id.number_of_volumes

    @api.onchange("first_volume")
    def _onchange_first_volume(self):
        if self.first_volume < 1:
            self.first_volume = 1

        if self.first_volume > self.last_volume:
            self.first_volume = self.last_volume

    @api.onchange("last_volume")
    def _onchange_last_volume(self):
        if self.last_volume > self.picking_id.number_of_volumes:
            self.last_volume = self.picking_id.number_of_volumes

        if self.last_volume < self.first_volume:
            self.last_volume = self.first_volume
