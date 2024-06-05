from odoo import models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def __document_comment_vals(self):
        res = super(FiscalDocumentLineMixinMethods, self).__document_comment_vals()
        res["lot"] = ", ".join(
            self.account_line_ids.mapped("prod_lot_ids").mapped("name")
        )
        res["lot_product_uom"] = ", ".join(
            self.account_line_ids.mapped("prod_lot_ids")
            .mapped("product_uom_id")
            .mapped("code")
        )
        res["lot_qty"] = ", ".join(
            map(str, self.account_line_ids.mapped("prod_lot_ids").mapped("product_qty"))
        )

        return res
