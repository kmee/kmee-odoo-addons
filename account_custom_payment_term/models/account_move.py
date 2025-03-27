# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_new_custom_term_from_current(self):
        """
        Action to copy the payment term as a custom term and assign it to the current record.
        """
        self.ensure_one()
        if not self.invoice_payment_term_id:
            raise UserError(_("The invoice has no payment term to copy!"))

        custom_term_id = self.invoice_payment_term_id.copy_term_id_as_custom(
            name=f"Custom: {self.name}"
        )
        self.invoice_payment_term_id = custom_term_id
