# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Commission Cron",
    "summary": """
        Sale Commission Cron""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_commission"],
    "data": [
        "data/cron_generate_commissions.xml",
    ],
}
