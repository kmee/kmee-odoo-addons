# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Folha Brasileira - Integração com o Ponto",
    "summary": "Horas extras, adicional noturno, faltas e dias trabalhados "
    "derivados da apuração de ponto, sem digitação manual",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Payroll",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "l10n_br_hr_payroll",
        "l10n_br_hr_attendance_apuracao",
    ],
    "data": [
        "data/hr_salary_rule_category_data.xml",
        "data/hr_salary_rule_data.xml",
        "views/hr_payslip_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
