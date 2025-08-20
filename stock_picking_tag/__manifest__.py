# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Picking Tags",
    "summary": "Allows to add multiple tags to stock pickings",
    "version": "15.0.1.1.0",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Inventory",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_view.xml",
        "views/stock_picking_tag_view.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
