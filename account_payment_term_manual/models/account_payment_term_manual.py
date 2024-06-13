# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentTermManual(models.Model):
    _name = "account.payment.term.manual"
    _inherit = "account.payment.term"

    def _default_line_ids(self):
        return [
            (
                0,
                0,
                {
                    "value": "balance",
                    "value_amount": 0.0,
                    "sequence": 9,
                    "days": 0,
                    "option": "day_after_invoice_date",
                },
            )
        ]

    origin_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        required=False,
    )

    has_manual_lines = fields.Boolean(
        help="Technical field to keep track of manual lines",
    )

    line_ids = fields.One2many(
        "account.payment.term.line.manual",
        "manual_payment_id",
        string="Terms",
        copy=True,
        default=_default_line_ids,
    )

    def unlink(self):
        return super(models.Model, self).unlink()

    def set_as_edited(self):
        if self.has_manual_lines:
            return
        if self.env.context.get("skip_manual_term_onchange"):
            return

        self.has_manual_lines = True
        self.name += " (edited)"


class AccountPaymentTermLineManual(models.Model):
    _name = "account.payment.term.line.manual"
    _inherit = "account.payment.term.line"

    manual_payment_id = fields.Many2one(
        "account.payment.term.manual",
        string="Payment Terms",
        required=True,
        index=True,
        ondelete="cascade",
    )

    payment_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        required=False,
    )

    fixed_date = fields.Date(
        string="Fixed Date",
        copy=False,
    )

    @api.constrains(
        "value",
        "value_amount",
        "days",
        "option",
        "day_of_the_month",
        "sequence",
        "fixed_date",
    )
    def _check_manual_payment_term_id(self):
        self.manual_payment_id.set_as_edited()
