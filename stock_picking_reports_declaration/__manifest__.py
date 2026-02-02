# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Picking Reports Declaration",
    "summary": """stock_picking_reports_declaration""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["stock"],
    "data": [
        "views/base_document_layout.xml",
        "views/report_stockpicking_operations.xml",
    ],
    "demo": [],
    "installable": True,
}
