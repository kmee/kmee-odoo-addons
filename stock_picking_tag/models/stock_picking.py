# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    tag_ids = fields.Many2many(
        comodel_name="stock.picking.tag",
        relation="stock_picking_tag_rel",
        column1="stock_picking_id",
        column2="tag_id",
        string="Tags",
    )
