# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Stock Available Stock Location",
    "summary": "Quantidade no estoque: só os locais de estoque dos armazéns",
    "version": "18.0.1.0.0",
    "category": "Warehouse Management",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "development_status": "Beta",
    "maintainers": ["mileo"],
    "depends": ["stock"],
    "data": [
        "views/product_product.xml",
        "views/product_template.xml",
    ],
    "demo": ["demo/stock_available_stock_location_demo.xml"],
    "installable": True,
}
