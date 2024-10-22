# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Hr Recruitment Job Share",
    "summary": """
        Share job in odoo portal""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "website_hr_recruitment",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_job.xml",
        "wizards/job_share.xml",
    ],
    "demo": [],
}
