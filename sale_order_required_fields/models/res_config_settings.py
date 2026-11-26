from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_require_payment_mode = fields.Boolean(
        related="company_id.sale_require_payment_mode", readonly=False
    )
    sale_require_payment_term = fields.Boolean(
        related="company_id.sale_require_payment_term", readonly=False
    )
    sale_require_line_date = fields.Boolean(
        related="company_id.sale_require_line_date", readonly=False
    )
