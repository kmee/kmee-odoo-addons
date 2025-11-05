# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    price_control_option = fields.Selection(
        [
            ("include_all_taxes", _("Include All Taxes")),
            ("remove_included_taxes", _("Remove Included Taxes")),
        ],
        string=_("Price Control Option"),
        help=_("Defines how the price unit is calculated for products in this category."),
    )
