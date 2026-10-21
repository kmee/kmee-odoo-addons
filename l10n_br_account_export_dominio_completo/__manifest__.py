# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Exportacao Contabil - Dominio com plano de contas",
    "summary": "Exporta lancamentos contabeis no layout do Dominio com plano de contas",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Alpha",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_account_export", "l10n_br_account_export_dominio"],
    "data": ["data/account_export_config.xml"],
    "installable": True,
}
