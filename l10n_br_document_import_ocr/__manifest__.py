# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Importação de documentos fiscais por OCR (Brasil)",
    "summary": "Importa NFS-e recebidas e faturas sem XML (PDF/imagem) com OCR",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "development_status": "Beta",
    "version": "16.0.1.0.0",
    "depends": [
        "l10n_br_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_view.xml",
        "views/document_import_extraction_view.xml",
        "wizards/document_import_wizard.xml",
    ],
    "installable": True,
    "external_dependencies": {
        "python": [
            "fitz",
        ]
    },
}
