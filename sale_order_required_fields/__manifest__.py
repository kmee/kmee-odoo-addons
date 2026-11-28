# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Required Fields",
    "summary": """
        Opções por empresa para exigir modo de pagamento, prazo de pagamento e
        data de entrega de cada linha no pedido de venda""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Sales",
    "depends": [
        "account_payment_sale",
        "sale_order_line_date",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sale_order.xml",
    ],
    "demo": [
        "demo/sale_order_demo.xml",
    ],
}
