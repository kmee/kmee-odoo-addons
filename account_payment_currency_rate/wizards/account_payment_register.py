# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):

    _inherit = "account.payment.register"

    change_rate = fields.Float(
        digits=(12, 6),
        default=1,
    )
    original_rate = fields.Float(
        digits=(12, 6),
        default=1,
        related="currency_id.rate",
        readonly=True,
    )
    change_rate_percent = fields.Float(
        digits=(12, 6),
    )

    @api.onchange("change_rate", "original_rate")
    def onchange_change_rate(self):
        self.change_rate_percent = self.change_rate / self.original_rate

    @api.onchange("original_rate")
    def onchange_currency_id(self):
        if self.original_rate:
            self.change_rate = self.original_rate

    @api.onchange("change_rate_percent")
    def onchange_change_rate_percent(self):
        if self.amount and (self.change_rate != self.original_rate):
            self.amount = self.amount * (self.change_rate_percent)
            self.payment_difference_handling = "reconcile"
            self.writeoff_label = "Cambio"

            if self.change_rate_percent > 1:
                self.writeoff_account_id = self.journal_id.profit_account_id
            elif self.change_rate_percent < 1:
                self.writeoff_account_id = self.journal_id.loss_account_id
