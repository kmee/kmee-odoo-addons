# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_sellers(self, params=False):
        sellers = super()._prepare_sellers(params)

        pricelist_rule = self.env.context.get("pricelist_rule")
        if (
            pricelist_rule
            and pricelist_rule.filter_by_pricelist_currency
            and pricelist_rule.pricelist_id.currency_id
        ):
            sellers_in_pricelist = sellers.filtered(
                lambda s: s.currency_id == pricelist_rule.pricelist_id.currency_id
            )
            if len(sellers_in_pricelist):
                return sellers_in_pricelist

        return sellers

    def _get_supplierinfo_pricelist_price(self, rule, date=None, quantity=None):
        self = self.with_context(pricelist_rule=rule)
        return super()._get_supplierinfo_pricelist_price(
            rule, date=date, quantity=quantity
        )
