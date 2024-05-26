# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SalePaymentTermManual(models.Model):

    _name = "sale.payment.term.manual"
    _inherit = "account.payment.term.manual.mixin"

    sale_order_id = fields.Many2one("sale.order")
    currency_id = fields.Many2one(
        "res.currency",
        related="sale_order_id.currency_id",
        readonly=True,
    )
