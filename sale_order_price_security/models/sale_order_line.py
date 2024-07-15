# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    can_edit_price_sale = fields.Boolean(
        "Can Edit Price in Sale",
        compute="_compute_can_edit_price_sale",
        store=False,
    )

    @api.onchange("product_id")
    def product_id_change(self):
        super().product_id_change()
        self._compute_can_edit_price_sale()

    def _compute_can_edit_price_sale(self):
        self.can_edit_price_sale = self.env["res.users"].has_group(
            "sale_order_price_security.group_sale_order_price_editor"
        )
