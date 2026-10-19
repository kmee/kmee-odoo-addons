# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Registro de Ponto Brasileiro - AFD",
    "summary": "Importação e geração do Arquivo Fonte de Dados (Anexo V da "
    "Portaria MTP 671/2021 e leiaute legado da 1.510/2009)",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "l10n_br_hr_attendance",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_br_hr_afd_import_views.xml",
        "wizards/l10n_br_hr_afd_export_wizard_views.xml",
        "views/l10n_br_hr_afd_menu.xml",
    ],
    "installable": True,
}
