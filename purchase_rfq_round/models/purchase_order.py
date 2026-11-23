# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    rfq_round_id = fields.Many2one(
        "purchase.rfq.round",
        string="Quotation Round",
        copy=False,
        index=True,
        readonly=True,
    )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    rfq_round_line_id = fields.Many2one(
        "purchase.rfq.round.line",
        string="Quotation Round Item",
        copy=False,
        index=True,
        readonly=True,
        ondelete="set null",
    )
    rfq_round_awarded = fields.Boolean(
        compute="_compute_rfq_round_awarded", string="Awarded"
    )

    @api.depends("rfq_round_line_id.awarded_po_line_id")
    def _compute_rfq_round_awarded(self):
        for line in self:
            line.rfq_round_awarded = (
                bool(line.rfq_round_line_id)
                and line.rfq_round_line_id.awarded_po_line_id == line
            )

    def _rfq_round_unit_price_cc(self):
        """Preço unitário sem impostos na moeda da empresa, para comparar."""
        self.ensure_one()
        if not self.product_qty:
            return 0.0
        rate = self.order_id.currency_rate or 1.0
        return self.price_subtotal / rate / self.product_qty

    def action_rfq_round_award(self):
        for line in self:
            line.rfq_round_line_id._award(line)
        return True
