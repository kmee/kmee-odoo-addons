# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MIS Builder Purchase Commitment by Due Date",
    "summary": "Pedidos de compra aprovados no fluxo de caixa, pelo vencimento",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "mis_builder",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/mis_purchase_commitment_due_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
