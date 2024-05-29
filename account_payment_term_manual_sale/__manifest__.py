# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Payment Term Manual",
    "summary": """
        Review the payment term installments before confirm the sale order and copy
        the due date to the invoice.""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "sale",
        "account_payment_term_manual",
    ],
    "data": [
        "security/sale_payment_term_manual.xml",
        "views/sale_order.xml",
    ],
    "demo": [
        "demo/sale_payment_term_manual.xml",
    ],
}
