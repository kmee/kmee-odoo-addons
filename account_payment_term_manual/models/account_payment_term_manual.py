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
                    "value": "percent",
                    "value_amount": 100.0,
                    "nb_days": 0,
                },
            )
        ]

    origin_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Original Payment Terms",
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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_referenced_terms(self):
        """The ids of this model are not ids of payment terms.

        The check of the payment term would block the deletion of manual terms that
        have the same id of a payment term used in an invoice.
        """

    def copy_data(self, default=None):
        # the copy goes to another document and keeps the name, without the
        # translated " (copy)" suffix that account.payment.term adds
        return models.BaseModel.copy_data(self, default=default)

    def set_as_edited(self):
        for term in self:
            if term.has_manual_lines or self.env.context.get(
                "skip_manual_term_onchange"
            ):
                continue
            term.has_manual_lines = True
            term.name += " (edited)"


class AccountPaymentTermLineManual(models.Model):
    _name = "account.payment.term.line.manual"
    _description = "Manual Payment Term Line"
    _inherit = "account.payment.term.line"

    manual_payment_id = fields.Many2one(
        "account.payment.term.manual",
        string="Manual Payment Terms",
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
        help="When set, it is the due date, regardless of the delay.",
    )

    @api.depends("manual_payment_id")
    def _compute_days(self):
        # the manual lines are not linked to a payment term (payment_id)
        for line in self:
            if not line.nb_days and len(line.manual_payment_id.line_ids) > 1:
                line.nb_days = line.manual_payment_id.line_ids[-2].nb_days + 30
            else:
                line.nb_days = line.nb_days

    @api.depends("manual_payment_id")
    def _compute_value_amount(self):
        for line in self:
            if line.value == "fixed":
                line.value_amount = 0
            else:
                percents = line.manual_payment_id.line_ids.filtered(
                    lambda r: r.value == "percent" and r != line
                )
                line.value_amount = 100 - sum(percents.mapped("value_amount"))

    def _get_due_date(self, date_ref):
        self.ensure_one()
        if self.fixed_date:
            return self.fixed_date
        return super()._get_due_date(date_ref)

    @api.constrains(
        "value",
        "value_amount",
        "delay_type",
        "nb_days",
        "fixed_date",
    )
    def _check_manual_payment_term_id(self):
        self.manual_payment_id.set_as_edited()
