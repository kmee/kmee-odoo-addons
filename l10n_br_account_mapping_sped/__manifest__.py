# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Plano Referencial da RFB (SPED)",
    "summary": "Liga os planos de contas de destino ao plano referencial da "
    "RFB, base do registro I051 do SPED Contabil (ECD)",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_account_mapping"],
    "data": [
        "views/account_mapping.xml",
        "views/res_company.xml",
    ],
    "installable": True,
}
