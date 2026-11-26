# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Industrialização por encomenda - fatura pelas ordens de produção",
    "summary": "Fatura da industrialização com o retorno do material utilizado e "
    "o serviço sobre a matéria-prima aplicada nas ordens de produção",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Localization",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "mrp",
        "l10n_br_stock_account",
        "l10n_br_stock_industrialization",
    ],
    "data": ["views/account_move_views.xml"],
    "demo": ["demo/l10n_br_mrp_industrialization_demo.xml"],
}
