from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("sale_order_template_id")
    def _onchange_sale_order_template_id_pricelist_sync(self):
        for record in self:
            if (
                record.sale_order_template_id
                and record.sale_order_template_id.pricelist_id
            ):
                record.pricelist_id = record.sale_order_template_id.pricelist_id
