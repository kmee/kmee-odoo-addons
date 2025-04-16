from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    bdr_id = fields.Many2one("res.users", string="BDR")
    sdr_id = fields.Many2one("res.users", string="SDR")
    closer_id = fields.Many2one("res.users", string="Closer")

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if not order.user_id and order.opportunity_id:
            order.user_id = order.opportunity_id.user_id
        return order
