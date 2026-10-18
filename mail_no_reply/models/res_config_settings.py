from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    email_no_reply = fields.Char(
        string="Email no-reply",
        readonly=False,
        related="company_id.email_no_reply",
    )
