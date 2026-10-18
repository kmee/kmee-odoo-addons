from odoo import fields, models


class FiscalDocumentLine(models.Model):
    _inherit = "l10n_br_fiscal.document.line"

    nfe40_med = fields.Many2one(
        comodel_name="nfe.40.med",
        string="Grupo de Medicamento",
        related="product_id.nfe40_med",
    )
