# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "BPMN Processes",
    "summary": "BPMN 2.0 diagrams inside Odoo: comments per task, live status, "
    "versions with semantic diff, three-way merge and an editor with lock",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["mail", "bus"],
    "data": [
        "security/bpmn_process_security.xml",
        "security/ir.model.access.csv",
        "wizards/bpmn_import_wizard_views.xml",
        "views/bpmn_element_views.xml",
        "views/bpmn_process_views.xml",
        "views/bpmn_process_version_views.xml",
        "views/bpmn_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bpmn_process/static/src/viewer/*",
        ],
        "web.assets_tests": [
            "bpmn_process/static/tests/tours/*.js",
        ],
    },
    "installable": True,
    "application": True,
}
