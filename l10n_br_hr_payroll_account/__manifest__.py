# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Contabilização da Folha de Pagamento Brasileira",
    "summary": "Integração contábil da folha de pagamento BR",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "payroll_account",
        "l10n_br_hr_payroll",
    ],
    "data": [
        "data/account_journal_data.xml",
    ],
    "demo": [
        "demo/account_demo.xml",
    ],
    "installable": True,
}
