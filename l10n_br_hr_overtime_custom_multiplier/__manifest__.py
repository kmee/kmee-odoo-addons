# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Br Hr Overtime Custom Multiplier",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "hr_attendance",
        "l10n_br_hr_holidays_public",
    ],
    "data": [
        "security/hr_attendance_exception.xml",
        "security/hr_overtime_multiplier_range.xml",
        #
        "views/hr_attendance_overtime.xml",
        "views/hr_overtime_multiplier_range.xml",
        "views/hr_attendance_exception.xml",
    ],
}
