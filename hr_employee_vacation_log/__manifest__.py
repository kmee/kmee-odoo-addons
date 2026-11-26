# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "HR Employee Vacation Log",
    "summary": "Simple log of vacation periods taken by each employee, "
    "with the accrual periods and a vacation schedule report",
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
        "views/hr_employee_vacation_period_views.xml",
        "views/hr_employee_vacation_views.xml",
        "views/hr_employee_views.xml",
        "wizard/hr_employee_vacation_schedule_wizard_views.xml",
        "report/hr_employee_vacation_schedule_report.xml",
    ],
    "demo": [
        "demo/hr_employee_vacation_demo.xml",
    ],
    "installable": True,
}
