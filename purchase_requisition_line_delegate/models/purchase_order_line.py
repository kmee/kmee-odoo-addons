# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    has_quotation_line = fields.Boolean(
        compute="_compute_has_quotation_line",
        help="The same product is in another quotation or order of the agreement.",
    )

    @api.depends("product_id", "order_id.requisition_id")
    def _compute_has_quotation_line(self):
        for line in self:
            siblings = line.order_id._get_sibling_orders()
            line.has_quotation_line = bool(line.product_id) and (
                line.product_id in siblings.order_line.product_id
            )

    def action_view_quotations(self):
        self.ensure_one()
        orders = self.order_id._get_sibling_orders().filtered(
            lambda o: self.product_id in o.order_line.product_id
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Quotations and Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.ids)],
        }
