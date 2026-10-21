# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_price = fields.Float(groups="product_cost_security.group_product_cost")
    margin = fields.Float(groups="product_cost_security.group_product_cost")
    margin_percent = fields.Float(groups="product_cost_security.group_product_cost")
