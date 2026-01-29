{
    "name": "Monetary Index Update - SELIC",
    "version": "16.0.1.0.0",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "summary": "Fetch and update SELIC rates from Banco Central do Brasil",
    "license": "LGPL-3",
    "depends": [
        "base",
        "monetary_index_update",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/monetary_index_data.xml",
        "data/ir_cron.xml",
        "wizard/monetary_index_selic_update_wizard.xml",
        "views/monetary_index_views.xml",
    ],
    "installable": True,
}
