# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        self.ensure_one()
        result = super()._get_price_unit()

        fiscal_field = self._fields.get("fiscal_operation_id")
        if not fiscal_field or not self.fiscal_operation_id:
            # Caso não tenha a Operação Fiscal não é uma caso do Brasil
            return result

        # Controla as opções de valores com ou sem imposto para o custo automatizado
        if self.fiscal_operation_id.fiscal_operation_type == "in":
            category = self.product_id.categ_id
            if not category or not category.price_control_option:
                return result

            qty = self.quantity_done or self.product_qty or self.product_uom_qty
            if not qty:
                return result

            option = category.price_control_option
            if option == "include_all_taxes":
                if "amount_taxed" not in self._fields:
                    return result
                return self.amount_taxed / qty
            if option == "remove_included_taxes":
                if (
                    "amount_untaxed" not in self._fields
                    or "amount_tax_included" not in self._fields
                ):
                    return result
                return (self.amount_untaxed - self.amount_tax_included) / qty

        return result
