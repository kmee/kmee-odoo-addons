# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models

from ..constants import ACTIVE_STATES, ALLOCATION_MODEL, DEBIT_MODEL


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_payment_line_vals(self, payment_order):
        """Copy the data of the DDA boleto allocated to the line.

        The digitable line, the bar code and the difference (interest, fine and
        discount) only exist at the boleto: the payment line of the order gets
        them here, so the difference goes to the write-off and the invoice is
        never edited.
        """
        vals = super()._prepare_payment_line_vals(payment_order)
        allocation = (
            self.env[ALLOCATION_MODEL]
            .sudo()
            .search(
                [
                    ("move_line_id", "=", self.id),
                    ("debit_id.state", "in", ACTIVE_STATES),
                ],
                limit=1,
            )
        )
        if allocation:
            vals.update(allocation.debit_id._dda_payment_line_vals(self))
        return vals


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model_create_multi
    def create(self, vals_list):
        partials = super().create(vals_list)
        lines = partials.debit_move_id | partials.credit_move_id
        self.env[DEBIT_MODEL].sudo()._dda_on_reconcile(lines)
        return partials
