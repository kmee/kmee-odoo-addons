from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        self.ensure_one()
        picking = self.picking_id
        if picking.van_type and picking.van_session_id:
            session = picking.van_session_id
            pricelist = session.pricelist_id
            if pricelist:
                price = pricelist._get_product_price(self.product_id, self.product_qty)
            else:
                price = self.product_id.lst_price
            if self.product_id.lot_valuated:
                return dict.fromkeys(self.lot_ids, price)
            return {self.env["stock.lot"]: price}
        return super()._get_price_unit()
