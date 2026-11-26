from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_require_payment_mode = fields.Boolean(string="Require Payment Mode")
    sale_require_payment_term = fields.Boolean(string="Require Payment Terms")
    sale_require_line_date = fields.Boolean(string="Require Line Delivery Date")
