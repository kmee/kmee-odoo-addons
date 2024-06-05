# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMovePaymentTermLine(models.Model):

    _name = "account.move.payment.term.line"
    _inherit = "account.payment.term.line"

    account_move_id = fields.Many2one("account.move")
    currency_id = fields.Many2one(
        "res.currency",
        related="account_move_id.currency_id",
        readonly=True,
    )
    payment_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        required=False,
        index=True,
        ondelete="cascade",
    )
    date_maturity = fields.Date()
    amount = fields.Monetary()
