# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Credit Analysis",
    "version": "16.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Credit consultation and risk analysis management",
    "author": "KMEE",
    "website": "https://github.com/kmee/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "base",
        "contacts",
        "mail",
    ],
    "data": [
        # Security
        "security/credit_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/ir_sequence_data.xml",
        "data/credit_cnae_data.xml",
        "data/credit_natureza_juridica_data.xml",
        "data/credit_config_data.xml",
        # Views
        "views/credit_company_views.xml",
        "views/credit_analysis_views.xml",
        "views/credit_restriction_views.xml",
        "views/credit_partner_views.xml",
        "views/credit_history_views.xml",
        "views/credit_cnae_views.xml",
        "views/credit_natureza_juridica_views.xml",
        "views/credit_config_views.xml",
        "views/res_partner_views.xml",
        "views/credit_menus.xml",
        # Reports
        "report/credit_analysis_report.xml",
        "report/credit_analysis_template.xml",
    ],
    "demo": [
        "demo/credit_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
