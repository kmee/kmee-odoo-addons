# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'SAC',
    'version': '15.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'KMEE INFORMATICA LTDA',
    'website': 'https://www.kmee.com.br',
    'depends': [
        'base',
        'mail',
        'utm',
        'base_kanban_stage',
        'l10n_br_base',
    ],
    'data': [
        'views/sac.xml',
        'views/sac_menu.xml',
        'views/sac_reason.xml',
        'views/sac_type.xml',
        'views/product_template.xml',
        'views/base_kanban_stage.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
}
