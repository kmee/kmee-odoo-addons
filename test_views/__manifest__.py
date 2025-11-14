# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Test Views",
    "summary": """View and usage improvements for Stock Valuation Layer""",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "base",
    ],
    "data": [
        "data/scheduled_actions.xml",
        "security/test_view_item_security.xml",
        "views/test_view_item_views.xml",
        "data/test_view_item_data.xml",
    ],
    "demo": [],
}
