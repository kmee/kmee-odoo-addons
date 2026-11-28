from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    origin_mo_move_line_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="industrialization_invoice_line_id",
        string="Consumo na ordem de produção",
        help="Movimentos de consumo das ordens de produção que geraram esta linha.",
    )

    def unlink(self):
        for line in self.filtered("origin_mo_move_line_ids"):
            # a linha apagada deixa de apontar para os movimentos: a fatura
            # guarda o vínculo para liberá-los se for cancelada
            if line.move_id.exists():
                line.move_id.origin_mo_move_line_ids = [
                    (4, move.id) for move in line.origin_mo_move_line_ids
                ]
        return super().unlink()
