# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):

    _name = "account.move"
    _inherit = [
        "account.move",
        "account.payment.term.manual.mixin",
    ]

    @api.onchange(
        "line_ids",
        "invoice_payment_term_id",
        "invoice_date_due",
        "invoice_cash_rounding_id",
        "invoice_vendor_bill_id",
    )
    def _onchange_recompute_dynamic_lines(self):
        if not self.invoice_payment_term_id:
            return super(AccountMove, self)._onchange_recompute_dynamic_lines()
        # Replace manual lines if:
        # 1. invoice term has changed directly
        # 2. invoice term has changed indirectly but no current manual term is set
        if (
            self.env.context.get("payment_term_id_view_onchange")
            or not self.manual_payment_term_id
        ):
            # Unlink and create seem to reset invoice_payment_term_id, here we store it
            # in a variable to set the term_id again at the END OF THE METHOD
            new_inv_term_id = self.invoice_payment_term_id

            # unlinks/creates happen in this method: _update_manual_payment_term_id
            self._update_manual_payment_term_id(self.invoice_payment_term_id)

            # END OF THE METHOD -> ensure term_id gets set to user defined value
            self.invoice_payment_term_id = new_inv_term_id

        super(AccountMove, self)._onchange_recompute_dynamic_lines()

    def _recompute_payment_terms_lines(self):
        return super(
            AccountMove,
            self.with_context(manual_payment_term_id=self.manual_payment_term_id),
        )._recompute_payment_terms_lines()

    @api.onchange("manual_payment_term_id")
    def _onchange_manual_payment_term_id(self):
        self._onchange_recompute_dynamic_lines()

    def recompute_payment_lines(self):
        self._onchange_recompute_dynamic_lines()
