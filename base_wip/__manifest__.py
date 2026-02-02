# Copyright 2020 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base Wip",
    "summary": """
        Base Work In Progress""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "base",
        "spreadsheet_dashboard",
    ],
    "data": [
        "security/base_wip.xml",
        "security/base_wip_report.xml",
        "views/base_abstract_wip.xml",
        "views/base_wip.xml",
    ],
    "demo": [],
    "installable": True,
}
