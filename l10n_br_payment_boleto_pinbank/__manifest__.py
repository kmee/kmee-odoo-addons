# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Integração Banco PINBank - Boleto Bancário",
    "summary": """
        Payment with PINBank""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_payment_boleto"],
    "data": [
        "data/payment_provider.xml",
        "data/ir_cron.xml",
        "views/payment_provider.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    'installable': False,
}
