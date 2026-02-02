# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Tier Validation Exceptions",
    "summary": """Sale Tier Validation Exceptions""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "sale_exception",
        "sale_tier_validation",
        "report_py3o",
    ],
    "data": [
        "data/tier_definition.xml",
        "views/sale_exception_confirm.xml",
        "views/sale_order.xml",
        "views/exception_rule.xml",
    ],
    "demo": [],
    "installable": True,
}
