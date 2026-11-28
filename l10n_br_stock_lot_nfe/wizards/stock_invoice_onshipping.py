from odoo import models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _get_invoice_line_values(self, moves, invoice_values, invoice):
        values = super()._get_invoice_line_values(moves, invoice_values, invoice)
        origin = moves.filtered("origin_nfe_id")[:1]
        if values and origin:
            values["origin_nfe_id"] = origin.origin_nfe_id.id
            values["origin_nfe_line_id"] = origin.origin_nfe_line_id.id
        return values
