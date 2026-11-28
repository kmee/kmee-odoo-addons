# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Product Manufacturer",
    "summary": "Manufacturer and part number in purchase order lines and reports",
    "version": "18.0.1.0.0",
    "category": "Inventory/Purchase",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["product_manufacturer", "purchase"],
    "data": [
        "views/purchase_order.xml",
        "report/purchase_quotation_templates.xml",
        "report/purchase_order_templates.xml",
    ],
    "demo": ["demo/purchase_product_manufacturer_demo.xml"],
    "installable": True,
}
