{
    "name": "MRP BoM Line Substitute",
    "summary": "Alternative components per BoM line, carried to the manufacturing "
    "order and replaced from the component picking",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "depends": ["mrp"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/stock_move_substitute_views.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_production_views.xml",
        "views/stock_picking_views.xml",
    ],
    "demo": ["demo/mrp_substitute_demo.xml"],
    "installable": True,
}
