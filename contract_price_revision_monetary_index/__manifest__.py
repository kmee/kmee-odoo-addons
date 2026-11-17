# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Contract Price Revision by Monetary Index",
    "summary": "Revise contract prices on the anniversary by a monetary index (IPCA)",
    "version": "18.0.1.0.0",
    "category": "Contract",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "contract_price_revision",
        "monetary_index_update",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/ir_cron.xml",
        "views/contract_contract.xml",
        "views/contract_line.xml",
        "wizards/contract_price_revision_views.xml",
    ],
    "installable": True,
}
