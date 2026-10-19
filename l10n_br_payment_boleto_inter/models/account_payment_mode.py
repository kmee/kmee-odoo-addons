# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMode(models.Model):

    _inherit = "account.payment.mode"

    payment_boleto_discount = fields.Float(
        string="Discount",
        help="Discount percentage to be applied if paid before due date",
    )
    payment_boleto_discount_days = fields.Integer(
        string="Discount Days",
        help="Number of days before due date to apply the discount",
    )
