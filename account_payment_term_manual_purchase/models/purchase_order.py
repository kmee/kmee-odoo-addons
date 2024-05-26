# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrder(models.Model):

    _inherit = "purchase.order"

    manual_payment_term_ids = fields.One2many(
        "purchase.payment.term.manual",
        "purchase_order_id",
        string="Manual Payment Terms",
    )
