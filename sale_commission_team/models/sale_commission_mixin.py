# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleCommissionMixin(models.AbstractModel):
    _inherit = "commission.mixin"

    @api.model
    def _prepare_team_agents_vals(self, team_agents):
        """Convert team agent records (crm.team.agent or
        res.partner.agent.team) into commission lines creation values."""
        return [
            (0, 0, {"agent_id": a.agent_id.id, "commission_id": a.commission_id.id})
            for a in team_agents
        ]

    def _compute_agents_with_team(
        self, team, partner, user, base_agents, settlement_type=None
    ):
        """Compute the agents following the sequence of the team commission rules.

        The same agent is never added twice, the first rule that returns it wins.
        Without team the standard behavior (base_agents) is kept. A team without
        rules gets no agents at all.
        """
        if not team or not partner:
            return base_agents

        rules = team.commission_rule_ids.sorted("sequence")
        final_agents = []
        seen_agents = set()
        for rule in rules:
            if rule.code == "team":
                current_agents = self._get_team_agents(team)
            elif rule.code == "team_partner":
                current_agents = self._get_team_partner_agents(team, partner)
            elif rule.code == "partner":
                current_agents = self._get_partner_agents(partner, settlement_type)
            elif rule.code == "salesman" and user:
                current_agents = []
                if user.agent and user.salesman_as_agent:
                    current_agents = [(0, 0, self._prepare_agent_vals(user))]
            else:
                current_agents = []
            for agent in current_agents:
                agent_id = agent[2]["agent_id"]
                if agent_id not in seen_agents:
                    final_agents.append(agent)
                    seen_agents.add(agent_id)

        if not rules:
            return []
        return final_agents or base_agents

    def _get_partner_agents(self, partner, settlement_type=None):
        """Agents of the partner, without team logic."""
        return super()._prepare_agents_vals_partner(
            partner, settlement_type=settlement_type
        )

    def _get_team_agents(self, team):
        """Agents configured directly in the team."""
        return self._prepare_team_agents_vals(team.agent_ids)

    def _get_team_partner_agents(self, team, partner):
        """Agents configured for the combination of team and partner."""
        return self._prepare_team_agents_vals(
            partner.agent_team_ids.filtered(lambda a: a.team_id == team)
        )
