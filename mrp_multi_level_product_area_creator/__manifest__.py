# Copyright 2025 KMEE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Multi Level Product Area Creator",
    "summary": "Wizard to create Product MRP Areas for products and their BOM components",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "mrp_multi_level",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/product_mrp_area_create.xml",
        "views/mrp_menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
}
