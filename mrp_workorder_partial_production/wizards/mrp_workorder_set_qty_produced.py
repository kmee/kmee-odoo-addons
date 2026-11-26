# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpWorkorderSetQtyProduced(models.TransientModel):
    _name = "mrp.workorder.set.qty.produced"
    _description = "Correct Work Order Quantity"

    workorder_id = fields.Many2one("mrp.workorder", required=True, ondelete="cascade")
    qty_produced = fields.Float(
        string="Quantity produced",
        digits="Product Unit of Measure",
        compute="_compute_qty_produced",
        store=True,
        readonly=False,
    )

    @api.depends("workorder_id")
    def _compute_qty_produced(self):
        for wizard in self:
            wizard.qty_produced = wizard.workorder_id.qty_produced

    def action_set_qty_produced(self):
        self.ensure_one()
        self.workorder_id.set_qty_produced(self.qty_produced)
        return {"type": "ir.actions.act_window_close"}
