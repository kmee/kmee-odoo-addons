# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "SST - Riscos Ocupacionais",
    "summary": "Ambientes, fatores de risco e laudos (PGR, LTCAT, PCMSO, AET)",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_esocial",
    ],
    "data": [
        "security/l10n_br_hr_sst_security.xml",
        "security/ir.model.access.csv",
        "views/sst_responsavel_views.xml",
        "views/sst_ambiente_views.xml",
        "views/sst_laudo_views.xml",
        "views/sst_risco_views.xml",
        "views/hr_job_views.xml",
        "views/hr_contract_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
