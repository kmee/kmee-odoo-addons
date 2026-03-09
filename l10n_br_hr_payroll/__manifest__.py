# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Folha de Pagamento Brasileira",
    "summary": "Folha de pagamento brasileira com INSS, IRRF, FGTS e verbas CLT",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "payroll",
        "l10n_br_hr",
        "l10n_br_hr_contract",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/hr_payroll_structure_data.xml",
        "views/hr_employee_views.xml",
        "views/hr_contract_views.xml",
        "views/hr_payslip_views.xml",
    ],
    "demo": [
        "demo/hr_employee_payroll_demo.xml",
        "demo/hr_contract_payroll_demo.xml",
        "demo/hr_payslip_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
}
