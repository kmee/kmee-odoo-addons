{
    "name": "Helpdesk Date Range",
    "version": "16.0.1.0.0",
    "category": "Helpdesk",
    "summary": "Add date range support to helpdesk tickets",
    "author": "Akretion",
    "website": "https://github.com/OCA/helpdesk",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "date_range",
    ],
    "data": [
        "views/helpdesk_ticket_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
