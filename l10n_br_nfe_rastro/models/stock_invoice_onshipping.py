from odoo import Command, models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _get_move_line_rastro_vals(self, move_line):
        """Build nfe40_rastro values from a stock.move.line with lot."""
        lot = move_line.lot_id
        if not lot:
            return False
        vals = {
            "nfe40_nLote": lot.name,
            "nfe40_qLote": move_line.quantity,
        }
        if lot.production_date:
            vals["nfe40_dFab"] = lot.production_date.date()
        if lot.expiration_date:
            vals["nfe40_dVal"] = lot.expiration_date.date()
        return vals

    def _get_invoice_line_values(self, moves, invoice_values, invoice):
        """Add the NF-e rastro (one per lot) to the invoice line values."""
        values = super()._get_invoice_line_values(moves, invoice_values, invoice)
        rastro = [
            Command.create(self._get_move_line_rastro_vals(move_line))
            for move_line in moves.move_line_ids.filtered("lot_id")
        ]
        if rastro:
            values["nfe40_rastro"] = rastro
        return values
