# Copyright 2024 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _build_invoice_values_from_pickings(self, pickings):
        """
        Build dict to create a new invoice from given pickings
        :param pickings: stock.picking recordset
        :return: dict
        """
        invoice, values = super()._build_invoice_values_from_pickings(pickings)

        pick = fields.first(pickings)

        if hasattr(pick, "sale_id") and hasattr(pick.sale_id, "payment_mode_id"):
            term_id = pick.sale_id.payment_term_id.id
            values["invoice_payment_term_id"] = term_id
            manual_term_id = pick.sale_id.manual_payment_term_id.copy().id
            values["manual_payment_term_id"] = manual_term_id
        elif hasattr(pick, "purchase_id") and hasattr(
            pick.purchase_id, "payment_mode_id"
        ):
            term_id = pick.purchase_id.payment_term_id.id
            values["invoice_payment_term_id"] = term_id
            manual_term_id = pick.purchase_id.manual_payment_term_id.copy().id
            values["manual_payment_term_id"] = manual_term_id

        return invoice, values

    def _action_generate_invoices(self):
        """
        Action to generate invoices based on pickings
        :return: account.move recordset
        """
        invoices = super()._action_generate_invoices()

        for inv in invoices:
            if inv.manual_payment_term_id:
                inv.financial_move_line_ids.with_context(
                    check_move_validity=False
                ).unlink()
                inv.with_context(check_move_validity=False).recompute_payment_lines()

        return invoices
