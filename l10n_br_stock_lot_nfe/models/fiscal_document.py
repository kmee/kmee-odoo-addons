from odoo import fields, models


class FiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def _compute_display_name(self):
        res = super()._compute_display_name()
        if self.env.context.get("show_name_for_lot_creation"):
            for document in self:
                document.display_name = (
                    f"{document.partner_id.name} Nota:{document.document_number}"
                )
        return res


class FiscalDocumentLine(models.Model):
    _inherit = "l10n_br_fiscal.document.line"

    origin_nfe_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Nota de Origem",
        copy=False,
    )
    origin_nfe_line_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.line",
        string="Linha na nota de Origem",
        copy=False,
    )

    def _compute_display_name(self):
        res = super()._compute_display_name()
        if self.env.context.get("show_name_for_lot_creation"):
            for line in self:
                line.display_name = (
                    f"{line.name} Qtd:{line.quantity} Unitário:{line.price_unit}"
                )
        return res
