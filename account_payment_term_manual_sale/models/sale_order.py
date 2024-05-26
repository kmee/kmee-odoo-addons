# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    manual_payment_term_ids = fields.One2many(
        "sale.payment.term.manual",
        "sale_order_id",
        string="Manual Payment Terms",
    )
