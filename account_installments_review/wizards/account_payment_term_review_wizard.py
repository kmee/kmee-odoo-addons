# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentTermReviewWizard(models.TransientModel):

    _name = "account.payment.term.review.wizard"

    account_move_id = fields.Many2one("account.move", readonly=True)
    company_id = fields.Many2one(related="account_move_id.company_id", readonly=True)

    date_reference = fields.Date(string="Date Reference", required=True)

    currency_id = fields.Many2one(
        "res.currency", readonly=True, related="account_move_id.currency_id"
    )
    payment_mode_id = fields.Many2one("account.payment.mode")
    invoice_payment_term_id = fields.Many2one("account.payment.term")
    line_ids = fields.One2many(
        "account.payment.term.line.review.wizard", "account_payment_term_review_id"
    )
    amount_tax = fields.Monetary(related="account_move_id.amount_tax")
    amount_untaxed = fields.Monetary(related="account_move_id.amount_untaxed")
    amount_by_group = fields.Binary(related="account_move_id.amount_by_group")
    amount_total = fields.Monetary(related="account_move_id.amount_total")
    invoice_payments_widget = fields.Text(
        related="account_move_id.invoice_payments_widget"
    )
    amount_residual = fields.Monetary(related="account_move_id.amount_residual")

    def _compute_payment_terms(self, date, total_balance, total_amount_currency):
        """Compute the payment terms.
        :param self:                    The current account.move record.
        :param date:                    The date computed by '_get_payment_terms_computation_date'.
        :param total_balance:           The invoice's total in company's currency.
        :param total_amount_currency:   The invoice's total in invoice's currency.
        :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
        """
        if self.invoice_payment_term_id:
            to_compute = self.invoice_payment_term_id.compute(
                total_balance, date_ref=date, currency=self.company_id.currency_id
            )
            if self.currency_id == self.company_id.currency_id:
                # Single-currency.
                return [(b[0], b[1], b[1]) for b in to_compute]
            else:
                # Multi-currencies.
                to_compute_currency = self.invoice_payment_term_id.compute(
                    total_amount_currency, date_ref=date, currency=self.currency_id
                )
                return [
                    (b[0], b[1], ac[1])
                    for b, ac in zip(to_compute, to_compute_currency)
                ]
        else:
            return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

    @api.onchange("invoice_payment_term_id")
    def onchange_payment_term_id(self):
        if self.invoice_payment_term_id != self.account_move_id.invoice_payment_term_id:
            others_lines = self.account_move_id.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type
                not in ("receivable", "payable")
            )
            total_balance = sum(
                others_lines.mapped(
                    lambda l: self.company_id.currency_id.round(l.balance)
                )
            )
            new_terms_lines = self._compute_payment_terms(
                self.date_reference, total_balance, self.amount_total
            )
            # self.line_ids = [(5, 0, 0)]  # Remove all existing lines.
            # for line in self.line_ids:
            # line.amount =
            for i, line in enumerate(new_terms_lines):
                self.line_ids = [
                    (
                        6,
                        0,
                        {
                            "date_maturity": line[0],
                            "amount": abs(line[1]),
                        },
                    )
                ]

    @api.onchange("account_move_id")
    def onchange_account_move_id(self):
        if self.account_move_id:
            # line_vals = [(5, 0, 0)]
            line_vals = [
                (
                    0,
                    0,
                    {
                        "date_maturity": line.date_maturity,
                        "amount": abs(line.debit or line.credit),
                        "account_move_line_id": line.id,
                    },
                )
                for line in self.account_move_id.line_ids.filtered(
                    lambda l: l.account_id.internal_type in ("receivable", "payable")
                ).sorted()
            ]
            self.update(
                {
                    "line_ids": line_vals,
                }
            )

    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        active_record = self.env[active_model].browse(active_id)

        res.update(
            {
                "account_move_id": active_id,
                "payment_mode_id": active_record.payment_mode_id.id,
                "invoice_payment_term_id": active_record.invoice_payment_term_id.id,
                "date_reference": active_record.invoice_date
                or fields.Date.context_today(self),
            }
        )
        return res

    def doit(self):
        for wizard in self:
            wizard.account_move_id.payment_mode_id = wizard.payment_mode_id
            wizard.account_move_id.invoice_payment_term_id = (
                wizard.invoice_payment_term_id
            )
            manual_payment_term_lines = [
                (line.date_maturity, line.amount) for line in wizard.line_ids
            ]
            wizard.account_move_id.with_context(
                installments_review=True,
                manual_payment_term_lines=manual_payment_term_lines,
            ).action_post()
        return {"type": "ir.actions.act_window_close"}


class AccountPaymentTermReviewWizard(models.TransientModel):

    _name = "account.payment.term.line.review.wizard"

    account_payment_term_review_id = fields.Many2one(
        "account.payment.term.review.wizard"
    )
    currency_id = fields.Many2one(
        "res.currency",
        readonly=True,
        related="account_payment_term_review_id.currency_id",
    )
    account_move_line_id = fields.Many2one("account.move.line")
    date_maturity = fields.Date()
    amount = fields.Monetary()
