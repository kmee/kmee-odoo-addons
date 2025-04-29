# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleBlanketOrder(models.Model):

    _inherit = "sale.blanket.order"

    quotation_data_json = fields.Json()

    isolated_quotation_id = fields.Many2one(
        comodel_name="sale.order",
        inverse_name="isolated_blanket_order_id",
        readonly=True,
        copy=False,
        string="Quotation",
    )

    def _compute_state(self):
        today = fields.Date.today()
        for order in self:
            if order.validity_date and order.validity_date <= today:
                order.state = "expired"
            else:
                order.state = "open"

    def create_sale_order(self):
        action_result = super().create_sale_order()

        sale_order_ids = action_result.get("domain", [])[0][2]
        if sale_order_ids:
            sale_orders = self.env["sale.order"].browse(sale_order_ids)
            for sale_order in sale_orders:
                sale_order.action_confirm()

        return action_result
