# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Afastamentos e Faltas - Folha BR",
    "summary": "Tipos de afastamento CLT para a folha de pagamento brasileira",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "hr_holidays",
        "l10n_br_hr_payroll",
    ],
    "data": [
        "views/hr_leave_type_views.xml",
        "data/hr_leave_type_data.xml",
    ],
    "installable": True,
}
