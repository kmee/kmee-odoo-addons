# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_agents_vals_partner(self, partner, settlement_type=None):
        """Override to use team logic."""
        return self._compute_agents_with_team(
            team=self.order_id.team_id,
            partner=partner,
            user=self.order_id.user_id.partner_id,
            base_agents=super()._prepare_agents_vals_partner(
                partner, settlement_type=settlement_type
            ),
            settlement_type=settlement_type,
        )

    @api.depends("order_id.team_id", "order_id.user_id")
    def _compute_agent_ids(self):
        """The team and the salesman are also triggers of the agents computation."""
        return super()._compute_agent_ids()
