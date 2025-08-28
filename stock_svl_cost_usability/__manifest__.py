# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock SVL Cost Usability",
    "summary": """View and usage improvements for Stock Valuation Layer""",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "stock",
        "stock_account",
        "web_widget_json_graph",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/stock_valuation_layer_and_cost_report.xml",
        "views/inventory_views.xml",
        "views/product_product.xml",
        "views/product_template.xml",
    ],
    "demo": [],
}
