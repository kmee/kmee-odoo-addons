# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"

    can_edit_price_purchase = fields.Boolean(
        string="Can Edit Price in Purchase",
        compute="_compute_can_edit_price_purchase",
    )

    def _compute_can_edit_price_purchase(self):
        can_edit = self.env.user.has_group(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )
        for line in self:
            line.can_edit_price_purchase = can_edit
