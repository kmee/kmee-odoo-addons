# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "SST - ASO e PCMSO",
    "summary": "Exames ocupacionais (NR-7), PCMSO e sigilo de dados de saúde",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_sst",
        "hr_employee_medical_examination",
    ],
    "data": [
        "security/l10n_br_hr_sst_aso_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/sst_pcmso_views.xml",
        "views/hr_employee_medical_examination_views.xml",
        "views/res_company_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
