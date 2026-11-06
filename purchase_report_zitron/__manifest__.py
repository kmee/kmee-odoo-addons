# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Report Zitron",
    "summary": "Zitron purchase order PDF layout",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase",
        "purchase_stock",
        "l10n_br_purchase",
        "purchase_order_line_sequence",
        "project_purchase",
    ],
    "data": [
        "data/report_paperformat.xml",
        "reports/purchase_order_cabecalho.xml",
        # primeira_pagina creates the company block that enderecos labels
        "reports/purchase_order_primeira_pagina.xml",
        "reports/purchase_order_enderecos.xml",
        "reports/purchase_order_linhas.xml",
        "reports/purchase_order_retrato.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
}
