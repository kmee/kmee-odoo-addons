{
    "name": "Monetary Index Update - Banco Central do Brasil",
    "version": "18.0.2.0.0",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "summary": "Fetch Brazilian indexes (SELIC, IPCA, INPC, IGP-M) from the BCB SGS",
    "license": "LGPL-3",
    "depends": [
        "base",
        "monetary_index_update",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/monetary_index_data.xml",
        "data/ir_cron.xml",
        "wizard/monetary_index_bacen_update_wizard.xml",
        "views/monetary_index_views.xml",
    ],
    "installable": True,
}
