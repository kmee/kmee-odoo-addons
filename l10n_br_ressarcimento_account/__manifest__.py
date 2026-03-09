# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Contabilização do Ressarcimento via Folha",
    "summary": "Lançamentos contábeis do reembolso de despesas na folha de pagamento",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_ressarcimento",
        "l10n_br_hr_payroll_account",
    ],
    "data": [
        "data/hr_salary_rule_account_data.xml",
    ],
    "demo": [
        "demo/account_demo.xml",
    ],
    "installable": True,
}
