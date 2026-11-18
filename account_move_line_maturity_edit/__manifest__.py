{
    "name": "Account Move Line - Maturity Edit",
    "summary": "Edit the due date of payable/receivable journal items, "
    "including posted entries, with a dedicated permission group",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    # Hard dependency on account_payment_order (OCA bank-payment), required
    # by the payment order guard so it needs no conditional lookup that could
    # silently disable itself.
    "depends": ["account", "account_payment_order"],
    "data": [
        "security/security.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
}
