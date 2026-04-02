# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrder(models.Model):

    _name = "purchase.order"
    _inherit = [
        "purchase.order",
        "account.payment.term.manual.mixin",
    ]

    @api.onchange("payment_term_id")
    def _onchange_payment_term_id(self):
        if not self.payment_term_id:
            return
        # Replace manual lines if:
        # 1. invoice term has changed directly
        # 2. invoice term has changed indirectly but no current manual term is set
        if (
            self.env.context.get("payment_term_id_view_onchange")
            or not self.manual_payment_term_id
        ):
            new_term_id = self.payment_term_id
            self._update_manual_payment_term_id(self.payment_term_id)
            self.payment_term_id = new_term_id

    ########################################
    # INVOICE DIRECTLY FROM PURCHASE ORDER #
    ########################################

    def _prepare_invoice(self):
        """Invoicing from PO: copy manual_payment_term_id to the invoice."""
        self = self.with_context(skip_manual_term_onchange=True)
        res = super()._prepare_invoice()

        if self.manual_payment_term_id:
            res["manual_payment_term_id"] = self.manual_payment_term_id.copy().id

        return res

    def action_create_invoice(self):
        """Create the invoice associated to the PO with manual term context."""
        self = self.with_context(skip_manual_term_onchange=True)
        result = super().action_create_invoice()

        # Recompute payment lines for invoices with manual terms
        for inv in self.invoice_ids:
            if inv.manual_payment_term_id:
                inv.recompute_payment_lines()

        return result
