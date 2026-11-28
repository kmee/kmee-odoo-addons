{
    "name": "MRP Component Return",
    "summary": "Return unused components from pre-production to stock",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "depends": ["mrp"],
    "data": [
        "views/stock_warehouse_views.xml",
        "views/mrp_production_views.xml",
    ],
    "demo": ["demo/mrp_component_return_demo.xml"],
    "installable": True,
}
