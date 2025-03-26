# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleCommissionMixin(models.AbstractModel):
    _inherit = "sale.commission.mixin"

    @api.model
    def _prepare_agents_team_vals_partner(self, partner_id, team_id):
        """Utility method for getting agents of a partner."""
        agent_team_ids = partner_id.agent_team_ids.filtered_domain(
            [("team_id", "=", team_id.id)]
        )
        if not agent_team_ids and team_id:
            agent_team_ids = self.env["crm.team.agent"].search(
                [("team_id", "=", team_id.id)]
            )

        return [
            (
                0,
                0,
                {
                    "agent_id": agent.agent_id.id,
                    "commission_id": agent.commission_id.id,
                },
            )
            for agent in agent_team_ids
        ]

    def _get_partner_agents(self, partner_id):
        """Get base partner agents without team logic."""
        return super()._prepare_agents_vals_partner(partner_id) or []

    def _compute_agents_with_team(self, team, partner_id, user_id, base_agents):
        """Compute agents based on configured rules sequence."""
        if not team or not partner_id:
            return base_agents

        final_agents = []
        rules = team.commission_rule_ids.sorted("sequence")
        seen_agents = {}  # Para controlar agentes já processados

        # If no rules defined, return empty list
        if not rules:
            return []

        for rule in rules:
            current_agents = []

            if rule.code == "team":
                current_agents = self._get_team_agents(team)

            elif rule.code == "team_partner":
                current_agents = self._get_team_partner_agents(team, partner_id)

            elif rule.code == "partner":
                current_agents = self._get_partner_agents(partner_id)

            elif rule.code == "salesman" and user_id:
                if user_id.agent and user_id.salesman_as_agent:
                    current_agents = [(0, 0, self._prepare_agent_vals(user_id))]

            for agent in current_agents:
                agent_id = agent[2]["agent_id"]
                if agent_id not in seen_agents:
                    final_agents.append(agent)
                    seen_agents[agent_id] = True

        return final_agents if final_agents else base_agents

    def _get_team_agents(self, team):
        """Get agents configured directly in the team."""
        return [
            (
                0,
                0,
                {
                    "agent_id": agent.agent_id.id,
                    "commission_id": agent.commission_id.id,
                },
            )
            for agent in team.agent_ids
        ]

    def _get_team_partner_agents(self, team, partner_id):
        """Get agents configured for the specific team and partner combination."""
        agent_team_ids = partner_id.agent_team_ids.filtered_domain(
            [("team_id", "=", team.id)]
        )
        return [
            (
                0,
                0,
                {
                    "agent_id": agent.agent_id.id,
                    "commission_id": agent.commission_id.id,
                },
            )
            for agent in agent_team_ids
        ]
