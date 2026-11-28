from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    pulled_from_stock = fields.Boolean()

    def _assign_picking(self):
        res = super()._assign_picking()
        for picking in self.filtered("pulled_from_stock").picking_id:
            if not picking.pulled_from_stock:
                picking.write(
                    {
                        "pulled_from_stock": True,
                        "display_pulled_from_stock_button": True,
                    }
                )
        return res
