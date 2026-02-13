{
    "name": "CRM Lead Stage Duration",
    "version": "16.0.1.0.0",
    "summary": "Track time spent by opportunities in each CRM stage",
    "category": "Sales/CRM",
    "author": "KMEE, Diego Paradeda",
    "website": "https://github.com/kmee/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": [
        "crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/crm_lead_stage_duration_views.xml",
    ],
    "installable": True,
    "application": False,
}
