# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Settlement(models.Model):
    _inherit = "commission.settlement"

    def _get_period_total(self):
        """Calculate total amount for the settlement period.

        Iterates over settlement lines and sums the invoice totals
        based on the commission configuration (amount_base_type and
        invoice_state).
        """
        total = 0.0
        for line in self.line_ids:
            commission = line.commission_id
            if commission.amount_base_type == "gross_amount":
                if commission.invoice_state == "open":
                    # In OCA 18.0 the settlement line references
                    # the source move via object_id on the commission line
                    total += line.settled_amount
            else:
                raise NotImplementedError(
                    "Amount base type %s not implemented"
                    % commission.amount_base_type
                )
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
                line.commission_line._compute_amount()
                line.settled_amount = line.commission_line.amount

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
