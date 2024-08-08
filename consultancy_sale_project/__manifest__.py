# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Consultancy Crm",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-private-addons",
    "depends": [
        "sale_project",
        "sale_timesheet",
        "contract_sale",
        "contract_variable_quantity",
        "contract_payment_mode",
        "product_contract",
        "subscription_oca",
        "contract_timesheet_invoice_type",
    ],
    "data": [
        "views/account_analytic_line.xml",
        "views/account_move_line.xml",
        "views/account_move.xml",
        "wizards/contract_create_project_wizard.xml",
        # 'security/contract_line.xml',
        # 'security/contract_contract.xml',
        #
        "security/ir.model.access.csv",
        #
        "views/contract_line.xml",
        "views/contract_contract.xml",
    ],
    "demo": [
        "demo/account_analytic_line.xml",
        "demo/contract_line.xml",
        "demo/contract_contract.xml",
    ],
}
