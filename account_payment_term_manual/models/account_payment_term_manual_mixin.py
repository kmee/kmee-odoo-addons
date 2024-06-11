# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentTermManualMixin(models.AbstractModel):

    _name = "account.payment.term.manual.mixin"

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

    def _update_manual_payment_term_id(self, term_id):
        """Check if invoice term has changed and replace manual term if needed."""
        if self.manual_payment_term_id.mapped("origin_term_id") == term_id:
            # Do nothing if manual term is already based on current term_id
            return

        self = self.with_context(skip_manual_term_onchange=True)

        # THIS SECTION IS ORDER SENSITIVE!
        new_manual_term = term_id.copy_data()[0]
        new_manual_term["origin_term_id"] = term_id.id
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
        self.with_context(
            skip_manual_term_onchange=True
        ).manual_payment_term_id = manual_term_id
