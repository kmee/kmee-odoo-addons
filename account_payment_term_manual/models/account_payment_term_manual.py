# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, Command


class AccountPaymentTermManual(models.Model):
    _name = "account.payment.term.manual"
    _inherit = "account.payment.term"
    _description = "Manual Payment Term"

    def _default_line_ids(self):
        return [
            Command.create(
                {
                    "value": "balance",
                    "value_amount": 0.0,
                    "days": 0,
                    "end_month": False,
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
    _description = "Manual Payment Term Line"

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

    def _get_due_date(self, date_ref):
        """Override to return fixed_date if set."""
        self.ensure_one()
        if self.fixed_date:
            return self.fixed_date
        return super()._get_due_date(date_ref)

    @api.constrains(
        "value",
        "value_amount",
        "days",
        "months",
        "end_month",
        "days_after",
        "fixed_date",
    )
    def _check_manual_payment_term_id(self):
        for record in self:
            if record.fixed_date:
                # Clear computed date fields when using fixed date
                pass
        self.manual_payment_id.set_as_edited()

    @api.onchange("fixed_date")
    def _onchange_fixed_date(self):
        for record in self:
            if record.fixed_date:
                # When fixed date is set, clear the relative date fields
                record.days = 0
                record.months = 0
                record.end_month = False
                record.days_after = 0
