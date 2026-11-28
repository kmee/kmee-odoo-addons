# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Stock Pulled From Stock",
    "summary": """
        Marca a entrega que puxou itens do estoque pela regra MTS+MTO""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Sales",
    "depends": [
        "sale_stock",
        "stock_mts_mto_rule",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/stock_picking_remove_mark.xml",
        "views/stock_picking_views.xml",
    ],
    "demo": [
        "demo/stock_picking_demo.xml",
    ],
}
