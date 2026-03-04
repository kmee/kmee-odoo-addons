# Copyright (C) 2025-Today - KMEE (https://www.kmee.com.br).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Workorder List View",
    "version": "16.0.1.0.0",
    "summary": "Easier workorder views: list first, open in current window",
    "category": "Manufacturing/Manufacturing",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "mrp_workorder",
    ],
    "data": [
        "views/mrp_workorder_act_window_views.xml",
    ],
    "installable": True,
    "application": False,
}
