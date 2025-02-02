# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrdeLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_agents_vals_partner(self, partner_id):
        """Add salesman agent if configured so and no other commission already populated."""
        base_agents = super()._prepare_agents_vals_partner(partner_id) or []
        return self._compute_agents_with_team(
            self.order_id.team_id, partner_id, base_agents
        )
