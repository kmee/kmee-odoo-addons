# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Ressarcimento via Folha de Pagamento",
    "summary": "Reembolso de despesas do empregado via folha de pagamento",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "hr_expense",
        "l10n_br_hr_payroll",
    ],
    "data": [
        "views/hr_expense_sheet_views.xml",
        "data/hr_salary_rule_data.xml",
    ],
    "installable": True,
}
