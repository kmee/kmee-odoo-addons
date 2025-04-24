from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    tier_id = fields.Many2one("res.partner.tier", string="Customer Tier")
