from odoo import fields, models


class StockPickingRemoveMark(models.TransientModel):
    _name = "stock.picking.remove_mark"
    _description = 'Remove the "Pulled From Stock" Mark'

    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Picking", required=True
    )

    def button_remove_mark(self):
        self.picking_id.display_pulled_from_stock_button = False
