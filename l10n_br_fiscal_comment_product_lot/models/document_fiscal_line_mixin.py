from odoo import models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def __document_comment_vals(self):
        res = super(FiscalDocumentLineMixinMethods, self).__document_comment_vals()

        lots = self.account_line_ids.mapped("prod_lot_ids")
        lot_info = []

        for lot in lots:
            lot_name = lot.name
            lot_product_uom = lot.product_uom_id.code if lot.product_uom_id else ""
            lot_qtys = (
                self.document_id.move_ids.mapped("picking_ids")
                .mapped("move_line_ids_without_package")
                .filtered(lambda line: line.lot_id == lot)
                .mapped("qty_done")
            )
            lot_qty = sum(lot_qtys)
            lot_info.append(f"{lot_name}, {lot_qty}, {lot_product_uom}")

        if lot_info:
            res["lot"] = "LOTE(S): " + "; ".join(lot_info)
        else:
            res["lot"] = ""

        return res
