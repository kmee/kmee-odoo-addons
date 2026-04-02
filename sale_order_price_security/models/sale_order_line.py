# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    can_edit_price_sale = fields.Boolean(
        "Can Edit Price in Sale",
        compute="_compute_can_edit_price_sale",
        store=False,
    )

    def _compute_can_edit_price_sale(self):
        can_edit = self.env.user.has_group(
            "sale_order_price_security.group_sale_order_price_editor"
        )
        for line in self:
            line.can_edit_price_sale = can_edit
