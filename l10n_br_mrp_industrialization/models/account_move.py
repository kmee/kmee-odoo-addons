from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    origin_mo_move_line_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="industrialization_invoice_id",
        string="Consumo de linhas apagadas",
        help="Movimentos de consumo cujas linhas foram apagadas da fatura. O "
        "vínculo é mantido para liberá-los se a fatura for cancelada.",
    )
    industrialization_production_ids = fields.Many2many(
        comodel_name="mrp.production",
        string="Ordens de produção",
        compute="_compute_industrialization_production_ids",
    )

    def _industrialization_moves(self):
        return self.origin_mo_move_line_ids | (
            self.invoice_line_ids.origin_mo_move_line_ids
        )

    @api.depends(
        "origin_mo_move_line_ids.raw_material_production_id",
        "invoice_line_ids.origin_mo_move_line_ids.raw_material_production_id",
    )
    def _compute_industrialization_production_ids(self):
        for move in self:
            move.industrialization_production_ids = (
                move._industrialization_moves().raw_material_production_id
            )

    def button_cancel(self):
        self._industrialization_moves().has_been_invoiced_industrialization = False
        return super().button_cancel()

    def unlink(self):
        self._industrialization_moves().has_been_invoiced_industrialization = False
        return super().unlink()
