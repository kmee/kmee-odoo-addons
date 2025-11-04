# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_sellers(self, params=False):
        sellers = super()._prepare_sellers(params=params)
        if params and params.get("order_id", False):
            currency_id = params.get("order_id", False).currency_id
            if currency_id:
                sellers = sellers.filtered(lambda s: s.currency_id == currency_id)
        return sellers
