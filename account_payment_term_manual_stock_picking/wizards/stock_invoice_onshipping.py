# Copyright 2024 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _build_invoice_values_from_pickings(self, pickings):
        """Use the payment term of the sale or purchase order of the picking.

        When the order has a manual payment term, a copy of it goes to the invoice.
        The order of the first picking is the one used, as the other values of the
        invoice.
        """
        invoice, values = super()._build_invoice_values_from_pickings(pickings)
        picking = fields.first(pickings)
        order = picking.sale_id or picking.purchase_id
        if order.payment_term_id:
            values["invoice_payment_term_id"] = order.payment_term_id.id
        if order.manual_payment_term_id:
            values["manual_payment_term_id"] = order.manual_payment_term_id.copy().id
        return invoice, values

    def _action_generate_invoices(self):
        """Synchronize the payment lines of the invoices that have a manual term."""
        invoices = super()._action_generate_invoices()
        invoices.filtered("manual_payment_term_id").recompute_payment_lines()
        return invoices
