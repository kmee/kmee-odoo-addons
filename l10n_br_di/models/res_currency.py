# Copyright (C) 2024-Today - KMEE (<https://kmee.com.br>).
# @author Luis Felipe Mileo <mileo@kmee.com.br>

from odoo import fields, models


class ResCurrency(models.Model):

    _inherit = "res.currency"

    siscomex_code = fields.Char()
