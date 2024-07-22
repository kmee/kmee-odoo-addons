# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Declaração de Importação",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "mail",
        "l10n_br_account",
        "l10n_br_nfe",
    ],
    "data": [
        "security/ir.model.access.csv",
        #
        "views/l10n_br_di_valor.xml",
        "views/l10n_br_di_pagamento.xml",
        "views/l10n_br_di_despacho.xml",
        "views/l10n_br_di_mercadoria.xml",
        "views/l10n_br_di_adicao.xml",
        "views/l10n_br_di_declaracao.xml",
        "views/res_currency.xml",
        #
        "views/account_move_view.xml",
        "views/nfe_adi_view.xml",
        "views/nfe_di_view.xml",
        "views/nfe_document_view.xml",
        "views/res_company.xml",
        #
        "data/res_currency.xml",
        #
        "wizards/l10n_br_di_importa_di_wizard.xml",
    ],
    "demo": [
        "demo/l10n_br_di_valor.xml",
        "demo/l10n_br_di_pagamento.xml",
        "demo/l10n_br_di_despacho.xml",
        "demo/l10n_br_di_mercadoria.xml",
        "demo/l10n_br_di_adicao.xml",
        "demo/l10n_br_di_declaracao.xml",
    ],
    "external_dependencies": {
        "python": ["xsdata"],
    },
}
