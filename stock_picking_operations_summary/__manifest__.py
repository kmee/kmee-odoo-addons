# Copyright (C) 2025-Today - KMEE (https://www.kmee.com.br).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Picking Operations Summary",
    "version": "16.0.1.0.0",
    "summary": "Grouped summary of stock moves by product and UoM on pickings",
    "category": "Inventory/Inventory",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
