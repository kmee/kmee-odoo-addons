{
    "name": "MRP Purchase Requisition",
    "summary": "Create purchase agreements from the components missing in a "
    "manufacturing order",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "depends": [
        "mrp",
        "purchase_requisition",
        "purchase_stock",
        "product_manufacturer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/mrp_production_purchase_requisition_views.xml",
        "views/mrp_production_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_requisition_views.xml",
        "views/purchase_requisition_line_views.xml",
    ],
    "demo": ["demo/mrp_production_demo.xml"],
    "installable": True,
}
