from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    linkedin_url = fields.Char(
        string="LinkedIn Profile",
        help="Partner's LinkedIn profile URL",
    )
