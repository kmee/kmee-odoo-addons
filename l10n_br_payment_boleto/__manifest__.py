# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Payment Boleto",
    "summary": """
        Base module for integrating boleto payment providers""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "payment",
        "account_payment_partner",
        "l10n_br_account_due_list",
        "l10n_br_base",
    ],
    "data": [
        "views/account_payment_mode.xml",
        "views/payment_transaction.xml",
    ],
    "demo": [],
}
