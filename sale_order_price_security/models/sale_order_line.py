# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    can_edit_price = fields.Boolean("Can Edit Price", compute="_compute_can_edit_price")

    def _compute_can_edit_price(self):
        self.can_edit_price = self.env["res.users"].has_group(
            "sale_order_price_security.group_sale_order_price_not_editor"
        )
