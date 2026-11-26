from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    origin = fields.Char(
        string="Compra de origem",
        compute="_compute_default_origin",
    )

    @api.depends("picking_id")
    def _compute_default_origin(self):
        for record in self:
            record.origin = record.picking_id.origin or False
