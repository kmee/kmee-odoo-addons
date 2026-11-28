# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Stock Lot Origin",
    "summary": "Registra no lote a separação, a compra e a venda de origem",
    "version": "18.0.1.0.0",
    "category": "Warehouse Management",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "depends": ["stock", "purchase_stock", "sale_stock"],
    "data": [
        "views/stock_lot.xml",
        "views/stock_move_line.xml",
    ],
    "demo": ["demo/stock_lot_origin_demo.xml"],
    "installable": True,
}
