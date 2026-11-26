from odoo import fields, models


class StockPickingFillNfe(models.TransientModel):
    _name = "stock.picking.fill.nfe"
    _description = "Preencher recebimento por NF-e"

    picking_id = fields.Many2one("stock.picking", required=True, ondelete="cascade")
    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="NF-e de entrada",
        required=True,
        domain="[('issuer', '=', 'partner'), ('fiscal_operation_type', '=', 'in')]",
    )

    def action_confirm(self):
        self.ensure_one()
        self.picking_id._fill_from_nfe(self.document_id)
        return {"type": "ir.actions.act_window_close"}
