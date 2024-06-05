# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    # def compute(self, value, date_ref=False, currency=None):
    #     manual_term_lines = self.env.context.get("manual_payment_term_line_ids")
    #     if manual_term_lines:
    #         sign = -1 if value < 0 else 1
    #         return [
    #             (line.date_maturity, sign * line.amount)
    #             for line in manual_term_lines
    #         ]
    #     return super().compute(value, date_ref=date_ref, currency=currency)
