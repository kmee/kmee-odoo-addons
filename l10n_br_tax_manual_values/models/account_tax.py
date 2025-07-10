# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_fiscal.constants.fiscal import FINAL_CUSTOMER_NO


class AccountTax(models.Model):

    _inherit = "account.tax"

    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        is_refund=False,
        handle_price_include=True,
        fiscal_taxes=None,
        operation_line=False,
        ncm=None,
        nbs=None,
        nbm=None,
        cest=None,
        cfop=None,
        discount_value=None,
        insurance_value=None,
        other_value=None,
        ii_customhouse_charges=None,
        freight_value=None,
        fiscal_price=None,
        fiscal_quantity=None,
        uot_id=None,
        icmssn_range=None,
        icms_origin=None,
        ind_final=FINAL_CUSTOMER_NO,
        **kwargs,
    ):
        pass

    def _compute_tax_base(self, tax, tax_dict, **kwargs):
        pass

    def _compute_icmsfcp(self, tax, taxes_dict, **kwargs):
        pass
