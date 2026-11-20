# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase RFQ Comparison",
    "summary": "Comparação multicritério das respostas da rodada de cotação",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase_rfq_round",
    ],
    "data": [
        "views/product_supplierinfo_views.xml",
        "views/purchase_rfq_round_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
