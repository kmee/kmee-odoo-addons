from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    is_industrialization = fields.Boolean(
        string="Recebimento para industrialização",
        help="Os recebimentos deste tipo recebem o material do cliente para "
        "industrialização: o estoque pertence ao cliente e os lotes são "
        "obrigatórios.",
    )
