# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Registro de Ponto Brasileiro (base)",
    "summary": "Marcacao de ponto imutavel com NSR e cadastro de REP "
    "(Portaria MTP 671/2021)",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "hr_attendance",
        "hr_contract",
        "l10n_br_hr",
    ],
    "external_dependencies": {"python": ["erpbrasil.base"]},
    "data": [
        "security/l10n_br_hr_attendance_security.xml",
        "security/ir.model.access.csv",
        "views/l10n_br_hr_rep_views.xml",
        "views/l10n_br_hr_marcacao_views.xml",
        "views/hr_attendance_views.xml",
        "views/hr_contract_views.xml",
        "views/l10n_br_hr_attendance_menu.xml",
    ],
    "installable": True,
}
