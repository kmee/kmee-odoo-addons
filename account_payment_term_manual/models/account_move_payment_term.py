# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMovePaymentTerm(models.Model):

    _name = "account.move.payment.term"
    _inherit = "account.payment.term.manual.mixin"

    account_move_id = fields.Many2one("account.move")
    currency_id = fields.Many2one(
        "res.currency",
        related="account_move_id.currency_id",
        readonly=True,
    )
