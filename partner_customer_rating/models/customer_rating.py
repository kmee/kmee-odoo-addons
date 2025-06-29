from odoo import fields, models


class CustomerRating(models.Model):
    _name = "customer.rating"
    _description = "Customer Satisfaction Rating"

    name = fields.Char(string="Customer Rating Description", required=True)
    image = fields.Binary(string="Rating Icon")
