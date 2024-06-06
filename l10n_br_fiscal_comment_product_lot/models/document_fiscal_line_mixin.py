from collections import defaultdict

from odoo import models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def __document_comment_vals(self):
        res = super(FiscalDocumentLineMixinMethods, self).__document_comment_vals()

        lot_info = []
        lot_quantities = defaultdict(float)
        lot_uom = {}

        for line in self.account_line_ids:
            line_lot_quantities = line.lots_grouped_by_quantity()
            for lot_name, qty in line_lot_quantities.items():
                lot_quantities[lot_name] += qty

                if lot_name not in lot_uom:
                    lot_uom[lot_name] = (
                        line.product_uom_id.code if line.product_uom_id else ""
                    )

        for lot_name, qty in lot_quantities.items():
            lot_product_uom = lot_uom.get(lot_name, "")
            lot_info.append(f"{lot_name}, {qty}, {lot_product_uom}")

        if lot_info:
            res["lot"] = "LOTE(S): " + "; ".join(lot_info)
        else:
            res["lot"] = ""

        return res
