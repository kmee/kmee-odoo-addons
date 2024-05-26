# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AcountMove(models.Model):

    _inherit = "account.move"

    manual_payment_term_ids = fields.One2many(
        "account.payment.term.manual",
        "account_move_id",
        string="Manual Payment Terms",
    )

    # def action_post(self):
    #     if self.is_invoice():
    #         if not self.env.context.get('installments_review'):
    #             action = self.env["ir.actions.actions"]._for_xml_id(
    #                 "account_installments_review.account_payment_term_review_wizard_act_window"
    #             )
    #             return action
    #     result = super().action_post()
    #     return result

    @api.onchange(
        "line_ids",
        "invoice_payment_term_id",
        "invoice_date_due",
        "invoice_cash_rounding_id",
        "invoice_vendor_bill_id",
    )
    def _onchange_recompute_dynamic_lines(self):
        super(AccountMove, self)._onchange_recompute_dynamic_lines()

        if self.invoice_payment_term_id:

            if self.manual_payment_term_ids:
                self.manual_payment_term_ids.unlink()
            manual_payment_term_lines = self.invoice_payment_term_id.compute(
                self.amount_total, self.invoice_date_due, self.currency_id
            )
            for line in manual_payment_term_lines:
                self.manual_payment_term_ids.create(
                    {
                        "account_move_id": self.id,
                        "date_maturity": line[0],
                        "amount": line[1],
                    }
                )

    def _recompute_payment_terms_lines(self):
        super(
            AccountMove,
            self.with_context(manual_payment_term_ids=self.manual_payment_term_ids.ids),
        )._recompute_payment_terms_lines()


class AccountPaymentTermManual(models.Model):

    _name = "account.payment.term.manual"

    account_move_id = fields.Many2one("account.move")
    currency_id = fields.Many2one(
        "res.currency", readonly=True, related="account_move_id.currency_id"
    )
    date_maturity = fields.Date()
    amount = fields.Monetary()
