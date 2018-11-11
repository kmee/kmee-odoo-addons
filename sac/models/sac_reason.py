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
