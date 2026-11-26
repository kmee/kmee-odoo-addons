# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Workorder Partial Production",
    "summary": "Record the quantity produced in each work order and "
    "post it to the manufacturing order from the last one",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Manufacturing/Manufacturing",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": ["mrp"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/mrp_workorder_register_production_views.xml",
        "wizards/mrp_workorder_set_qty_produced_views.xml",
        "views/mrp_workorder_views.xml",
    ],
    "demo": ["demo/mrp_demo.xml"],
    "installable": True,
}
