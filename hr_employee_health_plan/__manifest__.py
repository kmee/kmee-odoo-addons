# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "HR Employee Health Plan",
    "summary": "Health and dental plans of each employee",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "maintainers": ["mileo"],
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_health_plan_views.xml",
        "views/hr_employee_views.xml",
    ],
    "demo": [
        "demo/hr_employee_health_plan_demo.xml",
    ],
    "installable": True,
}
