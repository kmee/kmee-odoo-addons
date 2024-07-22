# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    di_mercadoria_ids = fields.Many2many(
        comodel_name="l10n_br_di.mercadoria",
    )
