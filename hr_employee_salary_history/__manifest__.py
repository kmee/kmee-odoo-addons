# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "HR Employee Salary History",
    "summary": "Current salary of the employee and the history of adjustments "
    "with their reasons",
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
        "views/hr_employee_salary_history_views.xml",
        "views/hr_employee_views.xml",
        "wizard/hr_employee_set_salary_views.xml",
    ],
    "demo": [
        "demo/hr_employee_salary_history_demo.xml",
    ],
    "installable": True,
}
