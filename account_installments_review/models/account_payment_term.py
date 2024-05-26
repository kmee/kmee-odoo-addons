# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def compute(self, value, date_ref=False, currency=None):
        if self.env.context.get("manual_payment_term_lines"):
            sign = value < 0 and -1 or 1
            manual_payment_term_lines = self.env.context.get(
                "manual_payment_term_lines"
            )
            result = []
            for line in manual_payment_term_lines:
                result.append((line[0], sign * line[1]))
            return result
        return super().compute(value, date_ref=date_ref, currency=currency)
