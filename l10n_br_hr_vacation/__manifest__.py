# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Férias e 13º Salário Brasileiros",
    "summary": "Férias CLT (art. 130), abono pecuniário e 13º salário",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_payroll",
        "hr_holidays",
    ],
    "data": [
        "data/hr_leave_type_data.xml",
        "data/hr_salary_rule_ferias_data.xml",
        "data/hr_salary_rule_13_data.xml",
        "data/hr_payroll_structure_data.xml",
        "views/hr_payslip_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
