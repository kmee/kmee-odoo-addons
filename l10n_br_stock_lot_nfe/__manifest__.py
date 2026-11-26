# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Lote com nota fiscal de origem",
    "summary": "Número, nota e linha da NF-e de origem no lote e no recebimento",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Localization",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "stock",
        "sale",
        "purchase",
        "l10n_br_fiscal",
        "l10n_br_stock_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/stock_picking_fill_nfe_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_quant_views.xml",
    ],
    "demo": ["demo/l10n_br_stock_lot_nfe_demo.xml"],
}
