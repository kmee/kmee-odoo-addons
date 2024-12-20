# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Brazilian Localization HR Recruitment",
    "summary": "Brazilian Localization HR Recruitment",
    "category": "Localization",
    "author": "KMEE, " "Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "version": "16.0.0.0.0",
    "depends": [
        "hr_recruitment",
        "l10n_br_hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_view.xml",
        "views/hr_applicant_view.xml",
    ],
    "test": [],
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
