{
    "name": "Monetary Index Update",
    "version": "16.0.1.0.0",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "summary": "Provides ability to update monetary values using indexes",
    "installable": True,
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/monetary_index_update_security.xml",
        "security/ir.model.access.csv",
        "data/admin_groups.xml",
        "views/monetary_index_views.xml",
        "wizard/monetary_update_by_index_wizard.xml",
    ],
}
