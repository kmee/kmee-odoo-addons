# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Registro de Ponto Brasileiro - Integridade do PTRP",
    "summary": "Resumo digital do escopo atestado e detecção de sobreposição "
    "em tempo de execução (art. 89 da Portaria MTP 671/2021)",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "l10n_br_hr_attendance_aej",
    ],
    "data": [
        "views/l10n_br_hr_apuracao_periodo_views.xml",
    ],
    "installable": True,
}
