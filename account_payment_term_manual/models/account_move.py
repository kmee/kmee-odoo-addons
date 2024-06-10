# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):

    _inherit = "account.move"

    manual_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term.manual",
        string="Manual Payment Term",
        copy=False,
    )

    manual_payment_term_line_ids = fields.One2many(
        comodel_name="account.payment.term.line.manual",
        related="manual_payment_term_id.line_ids",
        string="Manual Payment Term Lines",
    )

    def _update_manual_payment_term_id(self):
        """Check if invoice term has changed and replace manual term if needed."""
        if (
            self.manual_payment_term_id.mapped("origin_term_id")
            == self.invoice_payment_term_id
        ):
            # Do nothing if manual term is already based on current term_id
            return

        self = self.with_context(skip_manual_term_onchange=True)
        # Unlink and create seem to reset invoice_payment_term_id, here we store it
        # in a variable to set the term_id again at the END OF THE METHOD
        new_inv_term_id = self.invoice_payment_term_id

        # THIS SECTION IS ORDER SENSITIVE!
        new_manual_term = self.invoice_payment_term_id.copy_data()[0]
        new_manual_term["origin_term_id"] = self.invoice_payment_term_id.id
        new_manual_term["active"] = False
        new_manual_term["note"] = ""
        # Split creation for term and term.lines
        new_line_ids = new_manual_term.pop("line_ids")
        new_manual_term["line_ids"] = False

        # DO NOT MOVE THIS UNLINK
        self.manual_payment_term_id.line_ids.unlink()
        self.manual_payment_term_id.unlink()
        # DO NOT MOVE THIS CREATE
        manual_term_id = self.manual_payment_term_id.create(new_manual_term)
        for line in new_line_ids:
            line[2]["manual_payment_id"] = manual_term_id.id
        manual_term_id.line_ids = manual_term_id.line_ids.create(
            nl[2] for nl in new_line_ids
        )
        self.manual_payment_term_id = manual_term_id

        # END OF THE METHOD -> ensure term_id gets set to user defined value
        self.invoice_payment_term_id = new_inv_term_id

    @api.onchange(
        "line_ids",
        "invoice_payment_term_id",
        "invoice_date_due",
        "invoice_cash_rounding_id",
        "invoice_vendor_bill_id",
    )
    def _onchange_recompute_dynamic_lines(self):
        # Replace manual lines if invoice term has changed
        if not self.env.context.get("skip_manual_term_generation"):
            self._update_manual_payment_term_id()

        super(AccountMove, self)._onchange_recompute_dynamic_lines()

    def _recompute_payment_terms_lines(self):
        return super(
            AccountMove,
            self.with_context(manual_payment_term_id=self.manual_payment_term_id),
        )._recompute_payment_terms_lines()

    @api.onchange("manual_payment_term_id")
    def _onchange_manual_payment_term_id(self):
        # Do nothing if new manual term was just duplicated from term_id
        if self.env.context.get("skip_manual_term_onchange"):
            return

        # Append (edited) to manual term name if it was manually edited
        if (
            self.manual_payment_term_id
            and not self.manual_payment_term_id.has_manual_lines
        ):
            self.manual_payment_term_id.has_manual_lines = True
            self.manual_payment_term_id.name += " (edited)"

        # Recompute with context
        self = self.with_context(skip_manual_term_generation=True)
        self._onchange_recompute_dynamic_lines()
