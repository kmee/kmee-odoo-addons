# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Industrialização por encomenda - estoque",
    "summary": "Recebimento dos insumos do cliente, devolução do material não "
    "utilizado e rota Apenas cobrança",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Localization",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "l10n_br_sale_stock",
        "l10n_br_stock_account",
        "l10n_br_stock_lot_nfe",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/fiscal_operation_data.xml",
        "data/stock_data.xml",
        "wizards/stock_industrialization_create_views.xml",
        "wizards/stock_industrialization_set_sale_views.xml",
        "views/sale_order_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_picking_views.xml",
    ],
    "demo": ["demo/l10n_br_stock_industrialization_demo.xml"],
}
