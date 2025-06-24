# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UomUom(models.Model):

    _inherit = "uom.uom"

    use_period_quantity = fields.Boolean(
        "Use Period-Based Calculation",
        default=False,
        help="Adjusts field visibility based on period calculation.",
    )
