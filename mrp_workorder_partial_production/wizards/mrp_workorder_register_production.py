# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpWorkorderRegisterProduction(models.TransientModel):
    _name = "mrp.workorder.register.production"
    _description = "Record Work Order Production"

    workorder_id = fields.Many2one("mrp.workorder", required=True, ondelete="cascade")
    available_production_qty = fields.Float(
        related="workorder_id.available_production_qty",
        digits="Product Unit of Measure",
    )
    qty_producing = fields.Float(
        string="Quantity produced",
        digits="Product Unit of Measure",
        compute="_compute_qty_producing",
        store=True,
        readonly=False,
    )

    @api.depends("workorder_id")
    def _compute_qty_producing(self):
        for wizard in self:
            wizard.qty_producing = wizard.workorder_id.available_production_qty

    def action_record_production(self):
        self.ensure_one()
        self.workorder_id.record_production(self.qty_producing)
        return {"type": "ir.actions.act_window_close"}
