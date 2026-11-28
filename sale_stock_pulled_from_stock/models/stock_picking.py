from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pulled_from_stock = fields.Boolean()
    display_pulled_from_stock_button = fields.Boolean(string="Pulled from stock")

    def open_remove_mark(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_stock_pulled_from_stock.act_stock_picking_remove_mark"
        )
        action["context"] = {"default_picking_id": self.id}
        return action
