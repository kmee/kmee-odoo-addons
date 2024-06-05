# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):

    _inherit = "account.move"

    manual_payment_term_line_ids = fields.One2many(
        "account.move.payment.term.line",
        "account_move_id",
        string="Manual Payment Term Lines",
        copy=False,
    )

    @api.onchange(
        "line_ids",
        "invoice_payment_term_id",
        "invoice_date_due",
        "invoice_cash_rounding_id",
        "invoice_vendor_bill_id",
    )
    def _onchange_recompute_dynamic_lines(self):
        term_lines = [tl.copy_data()[0] for tl in self.invoice_payment_term_id.line_ids]
        new_line_ids = self.manual_payment_term_line_ids.create(term_lines)
        self.manual_payment_term_line_ids = new_line_ids

        super(AccountMove, self)._onchange_recompute_dynamic_lines()

        # if self.manual_payment_term_line_ids:
        #     self.manual_payment_term_line_ids = False

        # if self.invoice_payment_term_id:
        #     manual_payment_term_lines = self.invoice_payment_term_id.compute(
        #         self.amount_total, self.invoice_date, self.currency_id
        #     )
        #     for line in manual_payment_term_lines:
        #         if line[1] > 0:
        #             self.manual_payment_term_line_ids += self.env[
        #                 "account.move.payment.term"
        #             ].create(
        #                 {
        #                     "account_move_id": self.id,
        #                     "date_maturity": line[0],
        #                     "amount": abs(line[1]),
        #                 }
        #             )

    # def _recompute_payment_terms_lines(self):
    #     return super(
    #         AccountMove,
    #         self.with_context(manual_payment_term_line_ids=self.manual_payment_term_line_ids),
    #     )._recompute_payment_terms_lines()
