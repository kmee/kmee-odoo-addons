# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = [
        "account.move",
        "account.payment.term.manual.mixin",
    ]

    @api.depends(
        "invoice_payment_term_id",
        "invoice_date",
        "currency_id",
        "amount_total_in_currency_signed",
        "invoice_date_due",
        "manual_payment_term_id",
        "manual_payment_term_id.has_manual_lines",
        "manual_payment_term_id.line_ids",
    )
    def _compute_needed_terms(self):
        """Override to inject manual payment term into context for each invoice.

        The compute method on account.payment.term checks the context
        for manual_payment_term_id and delegates to it if present.
        """
        invoices_with_manual = self.filtered(lambda inv: inv.manual_payment_term_id)
        invoices_without_manual = self - invoices_with_manual

        if invoices_without_manual:
            super(AccountMove, invoices_without_manual)._compute_needed_terms()

        for invoice in invoices_with_manual:
            super(
                AccountMove,
                invoice.with_context(
                    manual_payment_term_id=invoice.manual_payment_term_id,
                ),
            )._compute_needed_terms()

    @api.onchange("invoice_payment_term_id")
    def _onchange_invoice_payment_term_id_manual(self):
        """Handle manual payment term update when payment term changes."""
        if not self.invoice_payment_term_id:
            return
        self._update_manual_payment_term_id(self.invoice_payment_term_id)

    @api.onchange("manual_payment_term_id")
    def _onchange_manual_payment_term_id(self):
        """Recompute when manual payment term changes."""

    def recompute_payment_lines(self):
        """Force recomputation of payment term lines."""
        self._compute_needed_terms()
