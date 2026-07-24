# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Relatórios da Folha de Pagamento BR",
    "summary": "Holerite, recibo de férias, rescisão e ficha de registro",
    "version": "16.0.1.1.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "l10n_br_hr_payroll",
        "l10n_br_hr_vacation",
    ],
    "data": [
        "report/report_holerite.xml",
        "report/report_ferias.xml",
        "report/report_rescisao.xml",
        "report/report_ficha_registro.xml",
        "report/report_actions.xml",
    ],
    "installable": True,
}
