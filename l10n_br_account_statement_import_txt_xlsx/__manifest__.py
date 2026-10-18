# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Account Statement Import Txt Xlsx",
    "summary": """
        Importação de Extratos Bancários TXT/XLS dos Bancos Brasileiros""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "account_statement_import_sheet_file",
    ],
    "data": [
        "data/map_data.xml",
    ],
}
