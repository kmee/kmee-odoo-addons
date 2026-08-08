# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Plano Referencial RFB 1 - PJ em Geral - Lucro Real",
    "summary": "Tabela oficial do plano referencial 1 da RFB "
    "(L100A, L300A, leiaute 12) para o registro I051 da ECD",
    "version": "16.0.12.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_account_mapping_sped"],
    "data": [
        "data/mapping_plan.xml",
        "data/l10n_br.account.mapping.account.csv",
    ],
    "installable": True,
}
