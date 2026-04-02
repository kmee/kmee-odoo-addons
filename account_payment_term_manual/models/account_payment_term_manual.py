# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentTermManual(models.Model):
    _name = "account.payment.term.manual"
    _description = "Manual Payment Term"
    _inherit = "account.payment.term"

    def _default_line_ids(self):
        return [
            (
                0,
                0,
                {
                    "value": "balance",
                    "value_amount": 0.0,
                    "nb_days": 0,
                    "delay_type": "days_after",
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
    _description = "Manual Payment Term Line"
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
    )

    delay_type = fields.Selection(
        selection_add=[("custom", "Custom")],
        ondelete={
            "custom": "set default",
        },
    )

    @api.constrains(
        "value",
        "value_amount",
        "nb_days",
        "delay_type",
        "fixed_date",
    )
    def _check_manual_payment_term_id(self):
        for record in self:
            if record.fixed_date and record.delay_type != "custom":
                record.delay_type = "custom"
        self.manual_payment_id.set_as_edited()

    @api.onchange("fixed_date")
    def _onchange_fixed_date(self):
        for record in self:
            if record.fixed_date:
                record.delay_type = "custom"
