# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Substituicao de Funcionarios - Folha BR",
    "summary": "Registro de substituicao temporaria de funcionarios",
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
        "security/ir.model.access.csv",
        "views/hr_substituicao_views.xml",
    ],
    "installable": True,
}
