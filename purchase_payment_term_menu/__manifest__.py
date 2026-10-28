# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Payment Terms Menu",
    "summary": "Manage payment terms from the Purchase app",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/purchase_menu.xml",
    ],
    "maintainers": ["mileo"],
}
