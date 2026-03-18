from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_van_driver = fields.Boolean(default=False)
