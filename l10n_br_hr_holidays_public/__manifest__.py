# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br HR Holidays Public",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "l10n_br_resource",
        "hr_holidays_public_city",
        "base_address_extended",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/l10n_br_public_holidays_wizard.xml",
    ],
}
