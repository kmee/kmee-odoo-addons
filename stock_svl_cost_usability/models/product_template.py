# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    valuation_layer_json_text = fields.Text(
        string="Stock Valuation Layer JSON",
        compute="_compute_valuation_layer_json_text",
        store=False,
        help="JSON text of stock valuation layer, used to display the stock valuation"
        " layer in the product form view.",
    )

    def _compute_valuation_layer_json_text(self):
        """Compute the JSON text of stock valuation layer for each product."""
        self.ensure_one()
        self.valuation_layer_json_text = "{}"
        if len(self.product_variant_ids) == 1:
            self.valuation_layer_json_text = (
                self.product_variant_ids.valuation_layer_json_text
            )

    def action_open_stock_valuation_layer(self):
        self.ensure_one()
        ppo = self.env["product.product"]
        if len(self.product_variant_ids) == 1:
            action = ppo._get_stock_valuation_layer_action(self.product_variant_ids.id)
        else:
            action = ppo._get_stock_valuation_layer_action()
            action["domain"] = [("product_id", "in", self.product_variant_ids.ids)]
        return action
