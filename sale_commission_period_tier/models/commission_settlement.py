# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class CommissionSettlement(models.Model):
    _inherit = "commission.settlement"

    def _get_period_line_base(self, line):
        """Signed base amount of a settlement line (negative for refunds)."""
        agent_line = line.invoice_agent_line_id
        inv_line = agent_line.object_id
        base = line.commission_id._get_period_base_amount(
            inv_line.price_subtotal, inv_line.product_id, inv_line.quantity
        )
        if "refund" in (agent_line.invoice_id.move_type or ""):
            base = -base
        return base

    def recalculate_period_commission(self):
        """Apply the tier reached in the period to the lines of the settlement.

        The total is computed per commission, with all the lines of the settlement
        (all of them share company, currency and period). Only the settled amount
        of the settlement line changes, the commission of the invoice stays as is.
        """
        for settlement in self.filtered(lambda s: s.state == "settled"):
            lines = settlement.line_ids.filtered(
                lambda x: x.invoice_agent_line_id
                and x.commission_id.commission_type == "period_section"
            )
            for commission in lines.commission_id:
                commission_lines = lines.filtered(
                    lambda x, commission=commission: x.commission_id == commission
                )
                bases = {
                    x: settlement._get_period_line_base(x) for x in commission_lines
                }
                percent = commission.calculate_period_section(sum(bases.values()))
                for line, base in bases.items():
                    line.settled_amount = settlement.currency_id.round(
                        base * percent / 100.0
                    )
        return True

    def action_recalculate_period_commission(self):
        return self.recalculate_period_commission()
