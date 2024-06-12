# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def compute(self, value, date_ref=False, currency=None):
        """Inherit compute to use manual term id if set."""
        manual_payment_term_id = self.env.context.get("manual_payment_term_id")
        if (
            manual_payment_term_id
            and manual_payment_term_id.has_manual_lines
            and self is not manual_payment_term_id
        ):
            return manual_payment_term_id.compute(
                value, date_ref=date_ref, currency=currency
            )
        return super().compute(value, date_ref=date_ref, currency=currency)
