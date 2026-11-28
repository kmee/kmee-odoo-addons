from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # O núcleo já traz a origem do movimento (related="move_id.origin"), que no recebimento de compra é o número
    # do pedido; aqui só o rótulo muda.
    origin = fields.Char(string="Compra de origem")
