# Copyright (C) 2025-Today - KMEE (<https://kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Landed Cost - Programmed Pickings (Undo / Schedule)",
    "version": "18.0.1.0.0",
    "summary": "Allow scheduling (programmed) pickings for landed costs and copy them "
    "to normal pickings when ready.",
    "category": "Inventory",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "LGPL-3",
    "depends": ["stock", "stock_landed_costs"],
    "data": [
        "views/stock_landed_cost_programmed_views.xml",
    ],
    "installable": True,
    "application": False,
}
