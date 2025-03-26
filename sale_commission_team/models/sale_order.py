# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_agents_vals_partner(self, partner_id):
        """Override to use team logic."""
        return self._compute_agents_with_team(
            team=self.order_id.team_id,
            partner_id=partner_id,
            user_id=self.order_id.user_id.partner_id,
            base_agents=super()._prepare_agents_vals_partner(partner_id) or [],
        )

    def _compute_agent_ids(self):
        """Override to handle team commission rules."""
        super()._compute_agent_ids()
        for record in self:
            record.agent_ids = False
            if record.order_id.partner_id:
                record.agent_ids = record._prepare_agents_vals_partner(
                    record.order_id.partner_id
                )
