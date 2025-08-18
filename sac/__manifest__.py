# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "SAC",
    "version": "18.0.1.0.1",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": [
        "base",
        "mail",
        "utm",
        "product",
        "l10n_br_base",
    ],
    "data": [
        "security/sac.xml",
        "security/sac_reason.xml",
        "security/sac_type.xml",
        "security/sac_print.xml",
        "security/sac_kanban_stage.xml",
        #
        "views/sac_menu.xml",
        "views/sac.xml",
        "views/sac_reason.xml",
        "views/sac_type.xml",
        "views/product_template.xml",
        "views/sac_kanban_stage.xml",
        "wizards/sac_print.xml",
        #
        "data/mail_template.xml",
        "data/sac_kanban_stage.xml",
        "data/ir_sequence_data.xml",
        "data/sac_reason.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
}
