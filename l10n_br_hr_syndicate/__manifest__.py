# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Sindicato - Folha de Pagamento BR",
    "summary": "Convenções coletivas, piso salarial e contribuição sindical",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_payroll",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_br_hr_syndicate_views.xml",
    ],
    "demo": [
        "demo/res_partner_union_demo.xml",
        "demo/l10n_br_hr_syndicate_demo.xml",
    ],
    "installable": True,
}
