# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from odoo import fields, models


class SacReason(models.Model):

    _name = b'sac.reason'
    _description = 'Sac Reason'

    name = fields.Char()
    kanban_color = fields.Selection(
        selection=[
            (1, '1 - Roxo'),
            (2, '2 - Branco'),
            (3, '3 - Cinza'),
            (4, '4 - Lilás'),
            (5, '5 - Pastel'),
            (6, '6 - Amarelo'),
            (7, '7- Verde'),
            (8, '8 - Azul'),
            (9, '9 - Laranja'),
        ],
        default=2,
    )
