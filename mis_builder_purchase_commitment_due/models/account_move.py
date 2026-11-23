# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _purchase_orders_for_commitment(self):
        return self.invoice_line_ids.purchase_line_id.order_id

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._purchase_orders_for_commitment()._sync_commitment_due()
        return res

    def button_draft(self):
        res = super().button_draft()
        self._purchase_orders_for_commitment()._sync_commitment_due()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._purchase_orders_for_commitment()._sync_commitment_due()
        return res
