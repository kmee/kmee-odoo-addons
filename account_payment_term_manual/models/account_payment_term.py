# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def _compute_terms(self, *args, **kwargs):
        """Use the manual payment term of the document when it has manual lines.

        The manual term is passed by the context (manual_payment_term_id). A manual
        term without edited lines is ignored and the original term is used.
        """
        manual_term = self.env["account.payment.term.manual"]
        manual_term_id = self.env.context.get("manual_payment_term_id")
        if manual_term_id and self._name == "account.payment.term":
            manual_term = manual_term.browse(manual_term_id).exists()
        if manual_term.has_manual_lines:
            return manual_term._compute_terms(*args, **kwargs)
        return super()._compute_terms(*args, **kwargs)
