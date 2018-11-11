# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Sac',
    'summary': """
        Serviço de Atendimento ao Consumidor""",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'KMEE INFORMATICA LTDA,Odoo Community Association (OCA)',
    'website': 'www.kmee.com.br',
    'depends': [
        'utm',
        'mail',
        'product',
        'l10n_br_zip',
        'base_kanban_stage',
    ],
    'data': [
        'views/base_kanban_stage.xml',
        'views/product_template.xml',
        'views/sac_menu.xml',
        'views/sac.xml',
        'views/sac_type.xml',
        'views/sac_reason.xml',
        'data/sac_reason.xml',
        # 'security/sac_type.xml',
        # 'security/sac_reason.xml',
        # 'security/sac.xml',
    ],
    'demo': [
        # 'demo/sac_type.xml',
        # 'demo/sac.xml',
    ],
}
