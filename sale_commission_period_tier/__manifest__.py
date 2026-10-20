# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Commission Period Tiers",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "license": "AGPL-3",
    "summary": "Commission rates by sales tiers in the settlement period",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["commission", "account_commission", "sale_commission"],
    "data": [
        "views/sale_commission_views.xml",
    ],
    "installable": True,
}
