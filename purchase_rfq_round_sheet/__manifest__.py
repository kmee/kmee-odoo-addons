# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase RFQ Round Spreadsheet",
    "summary": "Planilha de resposta na rodada de cotação: envio e importação",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase_rfq_round",
    ],
    "external_dependencies": {"python": ["openpyxl", "xlsxwriter"]},
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_rfq_round_views.xml",
        "wizards/purchase_rfq_round_import_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
