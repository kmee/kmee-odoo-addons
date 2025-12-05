{
    "name": "Monetary Update",
    "version": "16.0.1.0.0",
    "author": "Management adn Accounting On-line",
    "summary": "Provides ability to update monetary values",
    "installable": True,
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/monetary_update_security.xml",
        "security/ir.model.access.csv",
        "views/monetary_update_index_views.xml",
        "views/monetary_update_field_state_views.xml",
        "wizard/new_monetery_track_wizard.xml",
        "wizard/update_field_by_index_wizard.xml",
    ],
}
