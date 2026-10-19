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

    @api.depends(
        "manual_payment_term_id",
        "manual_payment_term_id.has_manual_lines",
        "manual_payment_term_id.line_ids.value",
        "manual_payment_term_id.line_ids.value_amount",
        "manual_payment_term_id.line_ids.months",
        "manual_payment_term_id.line_ids.days",
        "manual_payment_term_id.line_ids.end_month",
        "manual_payment_term_id.line_ids.days_after",
        "manual_payment_term_id.line_ids.fixed_date",
    )
    def _compute_needed_terms(self):  # pylint: disable=missing-return
        for move in self:
            super(
                AccountMove,
                move.with_context(
                    manual_payment_term_id=move.manual_payment_term_id.id
                ),
            )._compute_needed_terms()

    def recompute_payment_lines(self):
        """Synchronize the payment term lines with the manual payment term.

        The sync of the dynamic lines compares the needed terms before and after a
        change. The change here is in the manual term, which was already
        considered, so the needed terms are reset to be recomputed inside the sync.
        """
        for move in self.filtered(lambda m: m.state == "draft" and m.is_invoice(True)):
            self.env.cache.set(move, move._fields["needed_terms"], {})
            self.env.cache.set(move, move._fields["needed_terms_dirty"], True)
            container = {"records": move}
            with move._check_balanced(container), move._sync_dynamic_lines(container):
                move.invalidate_recordset(["needed_terms", "needed_terms_dirty"])
