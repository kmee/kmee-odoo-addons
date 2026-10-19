# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Payment Boleto Inter",
    "summary": """Payment with Inter""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "l10n_br_payment_boleto",
        "website",
        "sale_management",
    ],
    "data": [
        "data/payment_provider.xml",
        "data/ir_cron.xml",
        "views/payment_provider.xml",
        "views/account_payment_mode.xml",
        "views/payment_transaction_templates.xml",
        "views/account_move_print_boleto.xml",
        "views/sale_order_print_boleto.xml",
    ],
    "demo": [],
}
