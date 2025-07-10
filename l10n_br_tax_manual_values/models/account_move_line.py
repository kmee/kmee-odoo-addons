# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .l10n_br_fiscal_document_line_mixin_methods import FISCAL_TAX_PREFIXES


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    def _get_manual_tax_values_from_context(self):
        tax_values = {}
        suffixes = ["_base_manual", "_value_manual"]

        for tax_prefix in FISCAL_TAX_PREFIXES:
            for suffix in suffixes:
                attr_name = tax_prefix + suffix
                tax_values[attr_name] = self.env.context.get(attr_name)

        return tax_values
