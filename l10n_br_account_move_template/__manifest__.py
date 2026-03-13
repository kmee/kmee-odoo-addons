# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Fiscal Account Move Template",
    "summary": "Configurable double-entry accounting templates for Brazilian fiscal documents",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Accounting",
    "depends": [
        "l10n_br_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_template_view.xml",
        "views/fiscal_operation_view.xml",
        "views/account_move_view.xml",
    ],
    "demo": [
        "demo/account_move_template_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
}
