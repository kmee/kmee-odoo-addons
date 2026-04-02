# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Line Qty Fields",
    "summary": "Display additional quantity fields on sale order lines",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_stock"],
    "data": [
        "security/security.xml",
        "views/res_config_settings.xml",
        "views/sale_order.xml",
    ],
}
