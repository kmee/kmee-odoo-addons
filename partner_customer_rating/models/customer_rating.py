from odoo import models, fields

class CustomerRating(models.Model):
    _name = 'customer.rating'
    _description = 'Customer Satisfaction Rating'

    name = fields.Char(string='Descrição', required=True)
    image = fields.Binary(string='Ícone')
