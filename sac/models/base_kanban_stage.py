# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from odoo import fields, models


class BaseKanbanStage(models.Model):

    _inherit = 'base.kanban.stage'

    mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string='Email Template',
        # domain="[('res_model_id', '=', 'model_id')]",
        help="If set an email will be sent to the customer "
             "when the sac reaches this step."
    )
