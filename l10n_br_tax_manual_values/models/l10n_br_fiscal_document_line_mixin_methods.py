# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

FISCAL_TAX_PREFIXES = [
    "icms",
    "icmsst",
    "issqn",
    "issqn_wh",
    "icmsst_wh",
    "ipi",
    "ii",
    "cofins",
    "cofinsst",
    "cofins_wh",
    "pis",
    "pisst",
    "pis_wh",
    "csll",
    "csll_wh",
    "irpj",
    "irpj_wh",
    "inss",
    "inss_wh",
]


class FiscalDocumentLineMixinMethods(models.AbstractModel):

    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def _prepare_br_manual_tax_dict(self):
        manual_tax_dict = {}
        suffixes = ["_base_manual", "_value_manual"]

        for tax_prefix in FISCAL_TAX_PREFIXES:
            for suffix in suffixes:
                attr_name = tax_prefix + suffix
                manual_tax_dict[attr_name] = getattr(self, attr_name)

        return manual_tax_dict

    def _compute_taxes(self, taxes, cst=None):
        pass
