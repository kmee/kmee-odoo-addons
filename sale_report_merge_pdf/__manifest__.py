# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Report Merge Pdf",
    "summary": """Merge pdf with sale base report""",
    "version": "20.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_management"],
    "data": [
        "views/sale_pdf_cover.xml",
        "views/sale_order_form.xml",
        "security/ir.access.csv",
    ],
    "external_dependencies": {
        "python": [
            "pypdf",
        ]
    },
}
