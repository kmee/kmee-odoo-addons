# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Historico Padrao Contabil",
    "summary": "Historicos padrao com template de variaveis para as partidas "
    "dos lancamentos contabeis",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_history.xml",
    ],
    "demo": ["demo/account_history_demo.xml"],
    "installable": True,
}
