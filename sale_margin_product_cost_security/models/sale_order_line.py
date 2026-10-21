# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .cost_security import COST_GROUP


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "sale.cost.security.mixin"]

    purchase_price = fields.Float(groups=COST_GROUP)
    margin = fields.Float(groups=COST_GROUP)
    margin_percent = fields.Float(groups=COST_GROUP)
