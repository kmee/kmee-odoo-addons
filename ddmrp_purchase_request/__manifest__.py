# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "DDMRP Purchase Request",
    "summary": "Buffers DDMRP enxergam as requisições de compra em andamento",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "ddmrp",
        "purchase_request",
    ],
    "data": [
        "views/stock_buffer_views.xml",
        "views/purchase_request_line_views.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
