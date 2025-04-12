# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Remove Odoo Word",
    "summary": """remove_odoo_word""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["base_setup", "web"],
    "data": [
        "views/res_config_settings_templates.xml",
    ],
    "assets": {
        "web.assets_backend_prod_only": [
            "remove_odoo_word/static/src/js/remove_odoo_title.js",
        ],
    },
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "qweb": [],
}
