# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty_available_stock = fields.Float(
        string="Quantity in Stock",
        compute="_compute_qty_available_stock",
        digits="Product Unit of Measure",
        help="Quantity on hand in the stock location of the warehouses and its "
        "sublocations, leaving out the other locations (input, output, "
        "production, transit).",
    )

    @api.model
    def _get_warehouse_stock_locations(self):
        return (
            self.env["stock.warehouse"]
            .search([("company_id", "in", self.env.companies.ids)])
            .lot_stock_id
        )

    @api.depends_context(
        "lot_id", "owner_id", "package_id", "from_date", "to_date", "company"
    )
    def _compute_qty_available_stock(self):
        locations = self._get_warehouse_stock_locations()
        products = self.with_context(location=locations.ids, warehouse_id=False)
        res = products._compute_quantities_dict(
            self.env.context.get("lot_id"),
            self.env.context.get("owner_id"),
            self.env.context.get("package_id"),
            self.env.context.get("from_date"),
            self.env.context.get("to_date"),
        )
        for product in self:
            product.qty_available_stock = res.get(product.id, {}).get(
                "qty_available", 0.0
            )

    def action_open_stock_quants(self):
        action = self.action_open_quants()
        locations = self._get_warehouse_stock_locations()
        action["domain"] = (action.get("domain") or []) + [
            ("location_id", "child_of", locations.ids)
        ]
        return action
