# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        """Since 17.0 the core refuses to cancel locked orders: unlock them
        for the cancellation and lock again the ones that were not cancelled
        (e.g. when the cancel confirmation wizard is shown)."""
        locked = self.filtered("locked")
        if not locked:
            return super().action_cancel()
        locked.action_unlock()
        try:
            return super().action_cancel()
        finally:
            locked.filtered(lambda order: order.state != "cancel").action_lock()
