{
    "name": "CRM Lead Stage Duration",
    "version": "20.0.1.0.0",
    "summary": "Track time spent by opportunities in each CRM stage",
    "category": "Sales/CRM",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "crm",
    ],
    "data": [
        "views/crm_lead_views.xml",
        "views/crm_lead_stage_duration_views.xml",
        "security/ir.access.csv",
    ],
    "installable": True,
    "application": False,
}
