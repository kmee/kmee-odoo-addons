# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"

    can_edit_price_purchase = fields.Boolean(
        "Can Edit Price in Purchase",
        compute="_compute_can_edit_price_purchase",
        store=False,
    )

    @api.onchange("product_id")
    def product_id_change(self):
        self._compute_can_edit_price_purchase()

    def _compute_can_edit_price_purchase(self):
        self.can_edit_price_purchase = self.env["res.users"].has_group(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )
