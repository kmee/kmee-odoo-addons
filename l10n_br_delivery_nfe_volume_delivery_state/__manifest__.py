# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Localization Delivery NFe - Volume Delivery State",
    "summary": "Delivery state and departure date of each NF-e volume, "
    "reflected in the stock move",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "development_status": "Beta",
    "version": "18.0.1.0.0",
    "depends": [
        "l10n_br_delivery_nfe_lot_volume",
    ],
    "data": [
        "views/stock_picking_view.xml",
        "views/stock_picking_vol_view.xml",
    ],
    "demo": [
        "demo/stock_picking_vol_demo.xml",
    ],
}
