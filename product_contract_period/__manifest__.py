{
    "name": "Sale Order Period",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale", "product_contract"],
    "data": [
        "views/sale_views.xml",
        "views/contract_views.xml",
        "views/product_views.xml",
        "views/sale_portal_templates.xml",
        "report/ir_actions_report_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "AGPL-3",
}
