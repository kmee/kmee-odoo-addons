# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    group_qty_available_today = fields.Boolean(
        "Qty Available Today",
        implied_group="sale_order_line_qty_fields.group_qty_available_today",
    )
    group_free_qty_today = fields.Boolean(
        "Free Qty Today",
        implied_group="sale_order_line_qty_fields.group_free_qty_today",
    )
    group_free_qty = fields.Boolean(
        "Free Qty", implied_group="sale_order_line_qty_fields.group_free_qty"
    )
