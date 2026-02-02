# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Hr Holidays Allocation Plan",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "hr_holidays",
        "hr_contract",
    ],
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "data": [
        "views/hr_employee.xml",
        "views/hr_leave_allocation.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
