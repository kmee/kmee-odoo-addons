# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Product Contract Period Bo",
    "summary": """product_contract_period_bo""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "product_contract_period",
        "sale_blanket_order",
        "sale_blanket_order_isolated_quotation",
        "uom",
    ],
    "data": [
        "views/uom_uom.xml",
        "views/sale_order.xml",
        "views/sale_blanket_order_line.xml",
    ],
    "demo": [],
    'installable': False,
}
