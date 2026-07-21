# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Commission Settlement Report Xlsx",
    "summary": "Export commission settlements as XLSX reports",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "account_commission_oca",
        "report_xlsx",
    ],
    "data": ["report/report_settlement_xlsx.xml"],
    "installable": True,
    "maintainers": ["mileo"],
}
