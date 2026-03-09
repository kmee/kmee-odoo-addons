# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Benefícios da Folha de Pagamento Brasileira",
    "summary": "VT, VR, VA, Plano de Saúde na folha de pagamento BR",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "payroll_contract_advantages",
        "l10n_br_hr_payroll",
    ],
    "data": [
        "data/hr_contract_advantage_template_data.xml",
        "data/hr_salary_rule_benefit_data.xml",
        "data/hr_payroll_structure_data.xml",
    ],
    "installable": True,
}
