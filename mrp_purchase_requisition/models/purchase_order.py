# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Destination MO",
        index=True,
    )
    production_origins = fields.Char(compute="_compute_production_origins")

    @api.depends("order_line.product_id", "requisition_id.line_ids.production_id")
    def _compute_production_origins(self):
        for order in self:
            products = order.order_line.product_id
            lines = order.sudo().requisition_id.line_ids.filtered(
                lambda line, products=products: line.production_id
                and line.product_id in products
            )
            order.production_origins = ", ".join(
                lines.production_id.mapped("display_name")
            )
