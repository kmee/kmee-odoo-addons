# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentTermManualMixin(models.AbstractModel):

    _name = "account.payment.term.line.manual.mixin"

    # currency_id = fields.Many2one(
    #     "res.currency",
    #     readonly=True,
    # )
    # date_maturity = fields.Date()
    # amount = fields.Monetary()
