# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase RFQ Round",
    "summary": "Rodada de cotação com vários fornecedores a partir de requisições",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase_requisition",
        "purchase_request",
        "queue_job",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_config_parameter_data.xml",
        "views/purchase_rfq_round_views.xml",
        "views/purchase_rfq_round_actions.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_line_views.xml",
        "wizards/purchase_request_line_make_rfq_round_views.xml",
        "wizards/purchase_rfq_round_award_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
