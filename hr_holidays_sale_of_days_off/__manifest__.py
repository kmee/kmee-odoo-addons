# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Hr Holidays Sale Of Days Off",
    "summary": """hr_holidays_sale_of_days_off""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "hr_holidays",
    ],
    "data": [
        "views/hr_leave_type.xml",
        "views/hr_leave_allocation.xml",
        "security/hr_leave_abono.xml",
        "views/hr_leave_abono.xml",
        "views/hr_employee.xml",
    ],
    "demo": [],
    "installable": True,
}
