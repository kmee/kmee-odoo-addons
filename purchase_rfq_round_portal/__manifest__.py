# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase RFQ Round Portal",
    "summary": "Fornecedor responde a cotação da rodada pelo portal",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase_rfq_round",
        "portal",
    ],
    "data": [
        "views/portal_templates.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
