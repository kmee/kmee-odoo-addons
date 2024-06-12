# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrder(models.Model):

    _name = "purchase.order"
    _inherit = [
        "purchase.order",
        "account.payment.term.manual.mixin",
    ]

    @api.onchange("payment_term_id")
    def _onchange_payment_term_id(self):
        if not self.payment_term_id:
            return
        # Replace manual lines if:
        # 1. invoice term has changed directly
        # 2. invoice term has changed indirectly but no current manual term is set
        if (
            self.env.context.get("payment_term_id_view_onchange")
            or not self.manual_payment_term_id
        ):
            new_term_id = self.payment_term_id
            self._update_manual_payment_term_id(self.payment_term_id)
            self.payment_term_id = new_term_id
