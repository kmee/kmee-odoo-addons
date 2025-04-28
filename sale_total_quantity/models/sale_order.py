from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_sale_product = fields.Integer(
        string="Total Products:", compute="_compute_totals"
    )
    total_sale_quantity = fields.Integer(
        string="Total Quantities:", compute="_compute_totals"
    )

    def _compute_totals(self):
        for record in self:
            record.total_sale_product = len(set(record.order_line.mapped("product_id")))
            record.total_sale_quantity = sum(
                record.order_line.mapped("product_uom_qty")
            )
