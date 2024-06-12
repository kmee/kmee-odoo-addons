# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):

    _name = "sale.order"
    _inherit = [
        "sale.order",
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

    def _prepare_invoice(self):
        """
        Invoicing from SO:
        Add prepare manual_term_id
        """
        res = super()._prepare_invoice()

        if self.manual_payment_term_id:
            res["manual_payment_term_id"] = self.manual_payment_term_id.copy().id

        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Invoicing from SO:
        Trigger manual term recompute lines
        """
        invoice_ids = super()._create_invoices(grouped=grouped, final=final, date=date)
        for inv in invoice_ids:
            if inv.manual_payment_term_id:
                inv.financial_move_line_ids.with_context(
                    check_move_validity=False
                ).unlink()
                inv.with_context(check_move_validity=False).recompute_payment_lines()
        return invoice_ids
