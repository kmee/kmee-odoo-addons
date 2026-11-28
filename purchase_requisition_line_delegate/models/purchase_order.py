# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_sibling_orders(self):
        """Other quotations and orders of the same agreement, not cancelled."""
        self.ensure_one()
        return self.requisition_id.purchase_ids.filtered(
            lambda o: o.state != "cancel" and o.id != (self._origin.id or self.id)
        )
