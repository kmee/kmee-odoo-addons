# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "eSocial - Eventos de SST",
    "summary": "S-2210 (CAT), S-2220 (ASO), S-2221 e S-2240 (agentes nocivos)",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_sst_epi",
        "l10n_br_hr_sst_aso",
        "l10n_br_hr_sst_cat",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/s2210_views.xml",
        "views/s2220_views.xml",
        "views/s2221_views.xml",
        "views/s2240_views.xml",
        "views/sst_cat_views.xml",
        "views/sst_laudo_views.xml",
        "views/menu_views.xml",
    ],
    "external_dependencies": {
        "python": ["esociallib"],
    },
    "installable": True,
}
