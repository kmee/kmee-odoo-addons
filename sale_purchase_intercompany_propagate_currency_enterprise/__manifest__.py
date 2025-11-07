# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Purchase Intercompany Propagate Currency Enterprise",
    "summary": """Propagate currency and pricelist from PO to SO on intercompany flow""",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "sale_purchase_inter_company_rules",
    ],
    "data": [
        "views/purchase_order_view.xml",
    ],
    "demo": [],
}
