# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Journal Security",
    "summary": "Restrict journals, entries and payments to user groups",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["account"],
    "data": [
        "security/account_journal_security.xml",
        "views/account_journal_views.xml",
    ],
    "installable": True,
}
