# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "DDMRP Purchase DLT Vendor Policy",
    "summary": "DLT do item comprado pelo pior prazo dos fornecedores homologados",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "ddmrp",
        "purchase_rfq_comparison",
    ],
    "data": [
        "views/stock_buffer_profile_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
