# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"

    hide_internal_reference = fields.Boolean()


class ProductProduct(models.Model):

    _inherit = "product.product"

    def get_product_multiline_description_sale(self):
        if self.product_tmpl_id.hide_internal_reference:
            name = self.name
        else:
            name = self.display_name
        if self.description_sale:
            name += "\n" + self.description_sale

        return name
