# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qty_available_stock = fields.Float(
        string="Quantity in Stock",
        compute="_compute_qty_available_stock",
        digits="Product Unit of Measure",
        help="Quantity on hand in the stock location of the warehouses and its "
        "sublocations, leaving out the other locations (input, output, "
        "production, transit).",
    )

    @api.depends("product_variant_ids.qty_available_stock")
    @api.depends_context(
        "lot_id", "owner_id", "package_id", "from_date", "to_date", "company"
    )
    def _compute_qty_available_stock(self):
        for template in self:
            template.qty_available_stock = sum(
                template.product_variant_ids.mapped("qty_available_stock")
            )

    def action_open_stock_quants(self):
        return self.product_variant_ids.action_open_stock_quants()
