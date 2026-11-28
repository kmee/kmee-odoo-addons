from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

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
