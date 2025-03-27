from odoo import fields, models


class SacType(models.Model):

    _name = 'sac.type'
    _description = 'Sac Type'

    name = fields.Char()
