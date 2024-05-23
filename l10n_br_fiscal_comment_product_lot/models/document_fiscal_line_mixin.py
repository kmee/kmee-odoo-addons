from odoo import models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def __document_comment_vals(self):
        res = super(FiscalDocumentLineMixinMethods, self).__document_comment_vals()
        res["lot"] = ", ".join(
            self.account_line_ids.mapped("prod_lot_ids").mapped("name")
        )
        return res
