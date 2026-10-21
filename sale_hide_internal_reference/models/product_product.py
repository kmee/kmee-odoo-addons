# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"

    hide_internal_reference = fields.Boolean()


class ProductProduct(models.Model):

    _inherit = "product.product"

    def get_product_multiline_description_sale(self, with_display_name=True):
        if not self.product_tmpl_id.hide_internal_reference:
            return super().get_product_multiline_description_sale(
                with_display_name=with_display_name
            )
        name = self.name if with_display_name else ""
        if self.description_sale:
            name += ("\n" if name else "") + self.description_sale
        return name
