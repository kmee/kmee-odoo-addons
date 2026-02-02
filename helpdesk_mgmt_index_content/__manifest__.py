# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Management Index Content",
    "summary": """
        Search tickets by attachment content""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["attachment_indexation", "helpdesk_mgmt"],
    "data": [
        "views/helpdesk_ticket_view.xml",
    ],
    "installable": True,
}
