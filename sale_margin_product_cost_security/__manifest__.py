# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Product Cost Security",
    "summary": "Restrict access to purchase_price field based on product cost security group",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_margin", "product_cost_security"],
    "data": [
        "views/sale_order_line_views.xml",
    ],
}
