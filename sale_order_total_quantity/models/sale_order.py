# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    total_units = fields.Integer(compute="_compute_total_units", store=True)

    @api.depends("order_line.product_uom_qty")
    def _compute_total_units(self):
        for order in self:
            total_units = 0
            for line in order.order_line:
                total_units += line.product_uom_qty
            order.total_units = total_units
