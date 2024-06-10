# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):

    _name = "sale.order"
    _inherit = [
        "sale.order",
        "account.payment.term.manual.mixin",
    ]

    @api.onchange("payment_term_id")
    def _onchange_payment_term_id(self):
        if self.env.context.get("payment_term_id_view_onchange"):
            new_term_id = self.payment_term_id
            self._update_manual_payment_term_id(self.payment_term_id)
            self.payment_term_id = new_term_id
