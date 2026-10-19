# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "SST - Folha de Pagamento",
    "summary": "Insalubridade e periculosidade a partir do laudo, e GILRAT adicional",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_sst",
        "l10n_br_hr_payroll",
    ],
    "data": [
        "data/hr_salary_rule_data.xml",
        "views/hr_contract_views.xml",
    ],
    "installable": True,
}
