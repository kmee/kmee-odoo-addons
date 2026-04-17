from odoo import models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _get_move_line_rastro_vals(self, move_line):
        """Build nfe40_rastro values from a stock.move.line with lot."""
        lot = move_line.lot_id
        if not lot:
            return False
        vals = {
            "nfe40_nLote": lot.name,
            "nfe40_qLote": move_line.qty_done,
        }
        if hasattr(lot, "production_date") and lot.production_date:
            vals["nfe40_dFab"] = lot.production_date
        if lot.expiration_date:
            vals["nfe40_dVal"] = lot.expiration_date.date()
        return vals

    def _build_fiscal_line_rastro(self, fiscal_line, stock_move):
        """Populate nfe40_rastro on fiscal document line from stock move lots."""
        rastro_vals = []
        for move_line in stock_move.move_line_ids.filtered(lambda ml: ml.lot_id):
            line_vals = self._get_move_line_rastro_vals(move_line)
            if line_vals:
                rastro_vals.append((0, 0, line_vals))
        if rastro_vals and hasattr(fiscal_line, "nfe40_rastro"):
            fiscal_line.write({"nfe40_rastro": rastro_vals})

    def _create_invoice_from_picking(self):
        """Override to add rastro data after invoice creation."""
        result = super()._create_invoice_from_picking()
        for wizard in self:
            for picking in wizard.picking_ids:
                invoice = picking.invoice_ids[:1]
                if not invoice:
                    continue
                for move in picking.move_ids:
                    if not move.move_line_ids.filtered(lambda ml: ml.lot_id):
                        continue
                    fiscal_line = invoice.fiscal_line_ids.filtered(
                        lambda fl: fl.product_id == move.product_id
                    )[:1]
                    if fiscal_line:
                        self._build_fiscal_line_rastro(fiscal_line, move)
        return result
