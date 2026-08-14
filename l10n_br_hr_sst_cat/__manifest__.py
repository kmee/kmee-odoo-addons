# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "SST - Acidente de Trabalho e CAT",
    "summary": "Registro de acidente, CAT e prazo do art. 22 da Lei 8.213/91",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_sst",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/sst_acidente_views.xml",
        "views/sst_cat_views.xml",
        "views/hr_employee_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
