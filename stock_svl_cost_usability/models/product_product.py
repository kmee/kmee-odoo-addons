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
        self.ensure_one()

        plot_dataset = [svl.unit_cost for svl in self.stock_valuation_layer_ids]
        labels = [
            svl.create_date.strftime("%b - %Y")
            for svl in self.stock_valuation_layer_ids
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
                    "yAxes": [
                        {
                            "ticks": {"beginAtZero": False, "stacked": False},
                            "scaleLabel": {"display": True, "labelString": "Quantity"},
                        }
                    ],
                    "xAxes": [
                        {
                            "scaleLabel": {"display": True, "labelString": "Date"},
                        }
                    ],
                },
                "elements": {"point": {"radius": 3}},
                # "legend": {"labels": {"usePointStyle": True}},
                "legend": {"display": False},
                "tooltips": {"intersect": False, "axis": "xy", "mode": "index"},
            },
        }
        self.valuation_layer_json_text = json.dumps(info)

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
