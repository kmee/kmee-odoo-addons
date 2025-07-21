{
    "name": "Partner Tier",
    "version": "16.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Add tier classification to partners",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "license": "LGPL-3",
    "depends": ["base_partner_company_group", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_tier_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/res_partner_tier_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
