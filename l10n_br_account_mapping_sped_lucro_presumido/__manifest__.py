# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Plano Referencial RFB 2 - PJ em Geral - Lucro Presumido",
    "summary": "Tabela oficial do plano referencial 2 da RFB "
    "(P100A, P150A, leiaute 12) para o registro I051 da ECD",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_account_mapping_sped"],
    "data": [
        "data/mapping_plan_l12.xml",
        "data/l12/l10n_br_account_mapping.account.csv",
    ],
    "installable": True,
}
