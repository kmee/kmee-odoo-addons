# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):

    _name = "account.move"
    _inherit = [
        "account.move",
        "account.payment.term.manual.mixin",
    ]

    @api.onchange("invoice_payment_term_id")
    def _onchange_invoice_payment_term_id(self):
        if not self.invoice_payment_term_id:
            return
        if (
            self.env.context.get("payment_term_id_view_onchange")
            or not self.manual_payment_term_id
        ):
            new_inv_term_id = self.invoice_payment_term_id
            self._update_manual_payment_term_id(self.invoice_payment_term_id)
            self.invoice_payment_term_id = new_inv_term_id

    def _compute_needed_terms(self):
        return super(
            AccountMove,
            self.with_context(manual_payment_term_id=self.manual_payment_term_id),
        )._compute_needed_terms()

    @api.onchange("manual_payment_term_id")
    def _onchange_manual_payment_term_id(self):
        self._compute_needed_terms()

    def recompute_payment_lines(self):
        self._compute_needed_terms()
