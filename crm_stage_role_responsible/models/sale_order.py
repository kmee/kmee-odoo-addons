from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sdr_bdr_id = fields.Many2one("res.users", string="SDR/BDR")
    hunter_id = fields.Many2one("res.users", string="Hunter")
    closer_id = fields.Many2one("res.users", string="Closer")
    farmer_id = fields.Many2one("res.users", string="Farmer")

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if not order.user_id and order.opportunity_id:
            order.user_id = order.opportunity_id.user_id
        return order
