{
    "name": "HR Overtime Report Action PDF",
    "version": "16.0.1.0.0",
    "summary": "Exporta PDF via menu Ações na list view hr.attendance.overtime",
    "author": "Seu Nome",
    "category": "Human Resources",
    "license": "AGPL-3",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["hr", "hr_attendance", "web", "l10n_br_hr_overtime_custom_multiplier"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_overtime_view_inherit.xml",
        "reports/overtime_report_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
