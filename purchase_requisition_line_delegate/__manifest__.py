# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Requisition Line Delegate",
    "summary": """
        Move purchase agreement lines to another agreement, show the totals by
        product and flag lines with justification or quantities in quotation.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "purchase_requisition",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/purchase_requisition_delegate.xml",
        "wizards/grouped_purchase_requisition.xml",
        "views/purchase_requisition.xml",
        "views/purchase_order.xml",
        "views/stock_picking.xml",
    ],
    "demo": [
        "demo/purchase_requisition.xml",
    ],
}
