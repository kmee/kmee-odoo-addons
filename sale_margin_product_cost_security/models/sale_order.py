# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .cost_security import COST_GROUP


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "sale.cost.security.mixin"]

    margin = fields.Monetary(groups=COST_GROUP)
    margin_percent = fields.Float(groups=COST_GROUP)
