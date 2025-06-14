from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_rating_id = fields.Many2one(
        'customer.rating',
        string='Satisfação do Cliente',
        tracking=True
    )

    @api.model
    def _search_customer_rating(self, operator, value):
        rating_ids = self.env['customer.rating'].search([('name', operator, value)]).ids
        return [('customer_rating_id', 'in', rating_ids)]
