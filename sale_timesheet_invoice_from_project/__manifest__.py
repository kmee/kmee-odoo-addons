# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Timesheet Invoice From Project",
    "summary": """sale_timesheet_invoice_from_project""",
    "version": "18.0.1.0.0",
    "category": "Project",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "project",
        "sale_timesheet",
    ],
    "data": ["views/project_menus.xml"],
    "demo": [],
    "installable": True,
}
