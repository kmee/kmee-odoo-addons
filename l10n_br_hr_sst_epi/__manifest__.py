# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "SST - EPI e Certificado de Aprovação",
    "summary": "Certificado de Aprovação (CA), ficha de entrega de EPI e NR-6",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_sst",
        "hr_employee_ppe",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/sst_ca_views.xml",
        "views/product_template_views.xml",
        "views/hr_personal_equipment_views.xml",
        "views/hr_employee_views.xml",
        "reports/ficha_epi_report.xml",
        "reports/ficha_epi_template.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
