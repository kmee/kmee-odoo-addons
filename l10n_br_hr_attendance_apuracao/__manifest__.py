# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Registro de Ponto Brasileiro - Apuração",
    "summary": "Motor de apuração da jornada: tolerância, intervalos, "
    "adicional noturno, horas extras, faltas e DSR (CLT)",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "l10n_br_hr_attendance",
        "l10n_br_hr_holidays_public",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_br_hr_ocorrencia_data.xml",
        "views/l10n_br_hr_ocorrencia_views.xml",
        "views/l10n_br_hr_apuracao_dia_views.xml",
        "views/l10n_br_hr_apuracao_periodo_views.xml",
        "views/res_config_settings_views.xml",
        "views/l10n_br_hr_apuracao_menu.xml",
    ],
    "installable": True,
}
