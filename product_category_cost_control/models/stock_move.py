# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        result = super()._get_price_unit()

        if not self.fiscal_operation_id:
            # Caso não tenha a Operação Fiscal não é uma caso do Brasil
            return result

        # Controla as opções de valores com ou sem imposto para o custo automatizado
        if self.fiscal_operation_id.fiscal_operation_type == "in":
            if (
                not self.product_id.categ_id.price_control_option
                or not self.product_qty
            ):
                return result

            option = self.product_id.categ_id.price_control_option
            if option == "include_all_taxes":
                return self.amount_taxed / self.product_qty
            elif option == "remove_included_taxes":
                return (
                    self.amount_untaxed - self.amount_tax_included
                ) / self.product_qty

        return result
