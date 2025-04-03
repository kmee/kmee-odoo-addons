from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"

    sac_ok = fields.Boolean(
        string="Visível no SAC",
    )
