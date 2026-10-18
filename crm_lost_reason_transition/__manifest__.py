# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "CRM Lost Reason Transition",
    "version": "20.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "summary": """
        Automatically route lost leads to specific teams and stages based on
        the loss reason and current stage.
    """,
    "depends": [
        "crm",
    ],
    "data": [
        "views/crm_lost_reason_transition.xml",
        "views/menus.xml",
        "security/ir.access.csv",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
