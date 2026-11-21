# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

SYNC_FIELDS = {"state", "payment_term_id", "date_planned", "order_line", "currency_id"}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _sync_commitment_due(self):
        self.env["mis.purchase.commitment.due"]._sync_orders(self)

    def write(self, vals):
        res = super().write(vals)
        if SYNC_FIELDS & vals.keys():
            self._sync_commitment_due()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def write(self, vals):
        res = super().write(vals)
        if {"product_qty", "price_unit", "taxes_id", "discount"} & vals.keys():
            self.order_id.filtered(
                lambda o: o.state in ("purchase", "done")
            )._sync_commitment_due()
        return res
