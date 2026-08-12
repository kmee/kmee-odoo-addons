# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "BR Payroll - Arquivos do Governo",
    "summary": "DIRF, SEFIP e CAGED (descontinuado): consulta de histórico apenas",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_payroll",
        "l10n_br_hr_benefit",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_br_hr_dirf_views.xml",
        "views/l10n_br_hr_sefip_views.xml",
        "views/l10n_br_hr_caged_views.xml",
        "views/res_company_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
