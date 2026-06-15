# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Helpdesk Mgmt Description Optimizer",
    "version": "16.0.1.0.0",
    "summary": "Summarize heavy helpdesk ticket descriptions, full content on demand",
    "category": "After-Sales",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": ["helpdesk_mgmt", "html_optimizer", "queue_job"],
    "data": [
        "data/reprocess.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "helpdesk_mgmt_description_optimizer/static/src/js/description_full.js",
        ],
    },
    "installable": True,
}
