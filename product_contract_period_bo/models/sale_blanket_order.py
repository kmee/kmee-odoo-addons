# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleBlanketOrder(models.Model):

    _inherit = "sale.blanket.order"

    def create_sale_order_from_wizard(self, sale_order_lines):
        action = super().create_sale_order_from_wizard(sale_order_lines)
        if action and action.get("domain"):
            domain = action["domain"]
            sale_order_ids = self.env["sale.order"].search(domain).ids
            for sale_order in self.env["sale.order"].browse(sale_order_ids):
                for line in sale_order.order_line:
                    line._onchange_period()
        return action
