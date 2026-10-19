# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Registro de Ponto Brasileiro - AEJ e Espelho de Ponto",
    "summary": "Arquivo Eletrônico de Jornada (Anexo VI) e espelho de ponto "
    "do PTRP, com assinatura ICP-Brasil",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "maintainers": ["mileo"],
    "depends": [
        "l10n_br_hr_attendance_apuracao",
    ],
    "external_dependencies": {"python": ["erpbrasil.assinatura"]},
    "data": [
        "data/ir_config_parameter_data.xml",
        "report/espelho_ponto.xml",
        "views/l10n_br_hr_apuracao_periodo_views.xml",
    ],
    "installable": True,
}
