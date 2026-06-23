# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    valuation_layer_json_text = fields.Text(
        string="Stock Valuation Layer JSON",
        compute="_compute_valuation_layer_json_text",
        store=False,
        help="JSON text of stock valuation layer, used to display the stock valuation"
        " layer in the product form view.",
    )

    def _compute_valuation_layer_json_text(self):
        """Compute the JSON text of stock valuation layer for each product."""
        for product in self:
            # Dataset should be sum of past SLV values divided by sum of past
            # SLV quantities
            plot_dataset = []
            total_value = 0
            total_quantity = 0
            for svl in product.stock_valuation_layer_ids:
                total_value += svl.value
                total_quantity += svl.quantity
                if total_quantity:
                    plot_dataset.append(total_value / total_quantity)

            labels = [
                svl.create_date.strftime("%b - %Y")
                for svl in product.stock_valuation_layer_ids
            ]

            info = {
                "type": "line",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "data": plot_dataset,
                            "fill": False,
                            "label": "Cost",
                            "borderWidth": 2,
                            "backgroundColor": "#a5d8d7",
                        }
                    ],
                },
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": False,
                            "title": {"display": True, "text": "Cost"},
                        },
                        "x": {
                            "title": {"display": True, "text": "Date"},
                        },
                    },
                    "elements": {"point": {"radius": 3}},
                    "plugins": {
                        "legend": {"display": False},
                        "tooltip": {
                            "intersect": False,
                            "axis": "xy",
                            "mode": "index",
                        },
                    },
                },
            }
            product.valuation_layer_json_text = json.dumps(info)

    def action_open_stock_valuation_layer(self):
        self.ensure_one()
        return self._get_stock_valuation_layer_action(self.id)

    @api.model
    def _get_stock_valuation_layer_action(self, product_id=None):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_account.stock_valuation_layer_action"
        )
        if product_id:
            action["context"] = {
                "search_default_product_id": product_id,
                "search_default_group_by_product_id": 1,
            }
        return action
