# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Invoice Manual Payment Term",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "account_payment_partner",
        "l10n_br_account_due_list",
        "base_sparse_field",
    ],
    "data": [
        "security/account_payment_term_manual.xml",
        "views/account_invoice_view.xml",
    ],
}
