from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    email_no_reply = fields.Char(
        string="No-Reply Email",
    )
