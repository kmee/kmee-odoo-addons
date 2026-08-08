# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Exportacao Contabil Brasileira",
    "summary": "Envia lancamentos contabeis aos sistemas usados pelos "
    "escritorios de contabilidade brasileiros",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Alpha",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["account", "l10n_br_base", "l10n_br_account_mapping"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/account_export.xml",
        "views/account_export_config.xml",
        "views/account_account.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
