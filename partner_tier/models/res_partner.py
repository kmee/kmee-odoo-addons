from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    tier_id = fields.Many2one(
        "res.partner.tier",
        string="Customer Tier",
        store=True,
    )

    def _commercial_fields(self):
        return super()._commercial_fields() + ["tier_id"]
