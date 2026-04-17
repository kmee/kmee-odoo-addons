{
    "name": "Account Move Picking Match or Create",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "account",
        "stock",
        "stock_picking_invoice_link",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_move_match_picking_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
}
