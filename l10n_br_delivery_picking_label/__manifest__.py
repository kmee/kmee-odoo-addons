# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Delivery Picking Label",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "l10n_br_stock_account",
        "l10n_br_delivery_nfe",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking.xml",
        "wizards/delivery_picking_label_wizard.xml",
        "report/report_delivery_picking_label.xml",
        "data/paperformat.xml",
        "data/report_delivery_picking_label.xml",
    ],
    "demo": [],
}
