# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Purchase Report Zitron",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/kmee/kmee-odoo-addons",
    "depends": [
        "purchase",
        "purchase_stock",
        "l10n_br_purchase",
        "purchase_order_line_sequence",
    ],
    "data": [
        "data/report_paperformat.xml",
        "reports/purchase_order_linhas.xml",
    ],
    "installable": True,
}
