# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Report Merge Pdf",
    "summary": """Merge pdf with sale base report""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_pdf_cover.xml",
        "views/sale_order_form.xml",
    ],
    "external_dependencies": {
        "python": [
            "pypdf",
        ]
    },
}
