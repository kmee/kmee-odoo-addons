# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import (division, print_function, unicode_literals,
                        absolute_import)
from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    sac_ok = fields.Boolean(
        string="Visível no SAC",
    )
