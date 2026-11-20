# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _ddmrp_dedup_key(self):
        self.ensure_one()
        if self.rfq_round_line_id:
            return ("round", self.rfq_round_line_id.id)
        group = self.order_id.purchase_group_id
        if group:
            return ("group", group.id, self.product_id.id)
        return None

    def _ddmrp_dedup_pick(self):
        awarded = self.filtered("rfq_round_awarded")
        if awarded:
            return awarded[:1]
        # Maior quantidade; no empate, a entrega mais cedo (conservador para
        # a janela do DLT) e, por fim, a linha mais antiga.
        return min(
            self,
            key=lambda line: (
                -line.product_qty,
                line.date_planned or line.create_date,
                line.id,
            ),
        )
