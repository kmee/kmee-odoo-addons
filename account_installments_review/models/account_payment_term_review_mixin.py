# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentTermReviewMixin(models.AbstractModel):

    _name = "account.payment.term.review.mixin"
    _description = "Account Payment Term Review Mixin"  # TODO

    name = fields.Char()
