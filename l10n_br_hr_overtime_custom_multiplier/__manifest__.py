# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Br Hr Overtime Custom Multiplier',
    'summary': """
        Module allows companies to apply a custom multiplier to overtime calculations in the Brazilian localization, providing flexible and configurable overtime management.""",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'KMEE,Odoo Community Association (OCA)',
    'website': 'https://kmee.com.br/',
    'depends': [
        'hr_attendance',
        'l10n_br_resource',
    ],
    'data': [
        'views/hr_attendance_overtime.xml',
        'views/res_config_settings.xml',
    ],
    'demo': [
    ],
}
