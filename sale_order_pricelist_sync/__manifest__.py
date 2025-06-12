# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Template Pricelist Sync",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "summary": """
        Sync pricelist from the quotation template into the sale order.
    """,
    "depends": ["sale_management"],
    "data": [
        "views/sale_order_template_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
