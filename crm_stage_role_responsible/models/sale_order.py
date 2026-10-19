from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sdr_bdr_id = fields.Many2one("res.users", string="SDR/BDR")
    hunter_id = fields.Many2one("res.users", string="Hunter")
    closer_id = fields.Many2one("res.users", string="Closer")
    farmer_id = fields.Many2one("res.users", string="Farmer")

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders.filtered(lambda o: not o.user_id and o.opportunity_id):
            order.user_id = order.opportunity_id.user_id
        return orders
