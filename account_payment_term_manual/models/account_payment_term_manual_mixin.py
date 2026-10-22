# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentTermManualMixin(models.AbstractModel):

    _name = "account.payment.term.manual.mixin"
    _description = "Account Payment Term Manual Mixin"

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

    has_manual_lines = fields.Boolean(
        related="manual_payment_term_id.has_manual_lines",
    )

    def _update_manual_payment_term_id(self, term_id):
        """Replace the manual term by a copy of term_id, if it is not a copy of it."""
        self.ensure_one()
        old_manual_term = self.manual_payment_term_id
        if old_manual_term.origin_term_id == term_id:
            # Do nothing if manual term is already based on current term_id
            return
        manual_term_model = self.env["account.payment.term.manual"].with_context(
            skip_manual_term_onchange=True
        )

        # the generic copy: account.payment.term.copy_data adds a translated
        # " (copy)" suffix to the name, which the manual term must not have
        vals = models.BaseModel.copy_data(term_id)[0]
        vals.update(
            {
                "origin_term_id": term_id.id,
                "active": False,
                "note": "",
                # the lines are created with the term, which needs its lines
                "line_ids": [
                    (0, 0, {k: v for k, v in line[2].items() if k != "payment_id"})
                    for line in vals["line_ids"]
                ],
            }
        )
        self.manual_payment_term_id = manual_term_model.create(vals)
        # the lines are deleted with the term (ondelete cascade)
        old_manual_term.unlink()
