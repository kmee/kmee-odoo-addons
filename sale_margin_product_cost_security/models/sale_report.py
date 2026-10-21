# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .cost_security import COST_GROUP


class SaleReport(models.Model):
    _name = "sale.report"
    _inherit = ["sale.report", "sale.cost.security.mixin"]

    margin = fields.Float(groups=COST_GROUP)
