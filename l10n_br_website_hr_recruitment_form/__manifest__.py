# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Brazilian Localization Website Hr Recruitment Form",
    "summary": """
        Brazilian Localization Website Hr Recruitment Form""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["website_hr_recruitment", "l10n_br_hr_recruitment"],
    "data": [
        "data/mail_template_data.xml",
        "views/hr_applicant_view.xml",
        "views/hr_recruitment_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_br_website_hr_recruitment_form/static/src/js/hr_application_form.js",
        ],
    'installable': False,
},
    'installable': False,
}
