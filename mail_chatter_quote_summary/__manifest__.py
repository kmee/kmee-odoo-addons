# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Chatter Quote Summary",
    "version": "16.0.1.0.0",
    "summary": "Collapse quoted email history in chatter messages, loaded on demand",
    "category": "Discuss",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": ["mail", "html_optimizer"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": [
            "mail_chatter_quote_summary/static/src/js/quote_history.js",
        ],
    },
    "installable": True,
}
