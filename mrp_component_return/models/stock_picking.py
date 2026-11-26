from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_final_mo_return = fields.Boolean(
        string="Return of All Components",
        copy=False,
        readonly=True,
        help="Created by the 'Return All' button of a manufacturing order.",
    )
