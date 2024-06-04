# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def compute(self, value, date_ref=False, currency=None):
        manual_payment_term_ids = self.env.context.get("manual_payment_term_ids")
        if manual_payment_term_ids:
            sign = -1 if value < 0 else 1
            return [
                (line.date_maturity, sign * line.amount)
                for line in manual_payment_term_ids
            ]
        return super().compute(value, date_ref=date_ref, currency=currency)
