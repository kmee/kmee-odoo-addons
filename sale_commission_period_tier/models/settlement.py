# Copyright 2025 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Settlement(models.Model):
    _inherit = "sale.commission.settlement"

    def _get_agent_line(self, settlement_line):
        return getattr(settlement_line, "agent_line_id", False) or getattr(
            settlement_line, "agent_line", False
        )

    def _get_agent_line_base_amount(self, agent_line):
        for attr in (
            "amount_base",
            "base_amount",
            "commission_base",
            "subtotal",
            "base",
        ):
            if hasattr(agent_line, attr):
                value = getattr(agent_line, attr)
                if value not in (False, None):
                    return value

        invoice_line = getattr(agent_line, "move_line_id", False) or getattr(
            agent_line, "invoice_line_id", False
        )
        if invoice_line and hasattr(invoice_line, "price_subtotal"):
            return invoice_line.price_subtotal

        sale_line = getattr(agent_line, "sale_line_id", False)
        if sale_line and hasattr(sale_line, "price_subtotal"):
            return sale_line.price_subtotal

        return 0.0

    def _get_period_total(self):
        total = 0.0
        for line in self.line_ids:
            agent_line = self._get_agent_line(line)
            if not agent_line:
                continue

            commission = agent_line.commission_id
            if commission.amount_base_type != "gross_amount":
                raise NotImplementedError(
                    "Amount base type %s not implemented"
                    % commission.amount_base_type
                )

            total += self._get_agent_line_base_amount(agent_line)
        return total

    def recalculate_period_commission(self):
        """Recalculate commission amounts based on period total sales"""
        self.ensure_one()
        if not self.agent_id.commission_id:
            return

        if self.agent_id.commission_id.commission_type != "period_section":
            return

        # Calculate period total
        total_amount = self._get_period_total()

        # Get applicable percentage
        percentage = self.agent_id.commission_id.calculate_period_section(total_amount)

        # Update commission lines with context to bypass validation
        with self.env.cr.savepoint():
            for line in self.with_context(
                period_commission_recalculation=percentage
            ).line_ids:
                agent_line = self._get_agent_line(line)
                if not agent_line:
                    continue
                agent_line._compute_amount()
                line.settled_amount = agent_line.amount

    def action_recalculate_period_commission(self):
        """Action to manually trigger commission recalculation"""
        for settlement in self:
            if settlement.state == "settled":
                settlement.recalculate_period_commission()
        return True

    def action_settle(self):
        """Override to add period commission recalculation"""
        res = super().action_settle()
        self.recalculate_period_commission()
        return res
