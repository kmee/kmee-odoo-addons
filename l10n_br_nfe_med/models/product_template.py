# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"

    nfe40_med = fields.Many2one(
        comodel_name="nfe.40.med",
        # delegate=True,
    )

    # eu tinha tentado fazer o delegate, mas não ficou bom,
    # da pra tentar fazer uma abordagem com Stacked.
