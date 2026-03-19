# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Blanket Order Isolated Quotation",
    "summary": """sale_blanket_order_isolated_quotation""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "sale_blanket_order",
        "sale_isolated_quotation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/sale_order_confirm.xml",
        "views/sale_blanket_order.xml",
        "views/sale_order.xml",
    ],
    "demo": [],
    "installable": True,
}
