# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models


class SaleBlanketOrderLine(models.Model):
    _inherit = "sale.blanket.order.line"

    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        default=0.0,
        help="Discount percentage to apply to the line",
    )
