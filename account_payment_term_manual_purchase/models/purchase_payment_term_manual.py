# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchasePaymentTermManual(models.Model):

    _name = "purchase.payment.term.manual"
    _inherit = "account.payment.term.manual.mixin"

    purchase_order_id = fields.Many2one("purchase.order")
    currency_id = fields.Many2one(
        "res.currency",
        related="purchase_order_id.currency_id",
        readonly=True,
    )
