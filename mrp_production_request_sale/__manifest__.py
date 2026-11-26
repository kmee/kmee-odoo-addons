{
    "name": "MRP Production Request Sale",
    "summary": "Production requests linked to the sale order that originated them",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "depends": ["mrp_production_request", "sale_mrp"],
    "data": [
        "views/sale_order_views.xml",
        "views/mrp_production_request_views.xml",
        "views/mrp_production_views.xml",
    ],
    "demo": ["demo/sale_order_demo.xml"],
    "installable": True,
}
