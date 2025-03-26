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

        # If no rules defined, fallback to default behavior
        if not rules:
            return self._compute_agents_legacy(team, partner_id, user_id, base_agents)

        for rule in rules:
            if rule.code == "team":
                team_agents = self._get_team_agents(team)
                final_agents.extend(team_agents)

            elif rule.code == "team_partner":
                team_partner_agents = self._get_team_partner_agents(team, partner_id)
                final_agents.extend(team_partner_agents)

            elif rule.code == "partner":
                partner_agents = self._get_partner_agents(partner_id)
                final_agents.extend(partner_agents)

            elif rule.code == "salesman" and user_id:
                if user_id.agent and user_id.salesman_as_agent:
                    final_agents.append((0, 0, self._prepare_agent_vals(user_id)))

        return final_agents if final_agents else base_agents

    def _compute_agents_legacy(self, team, partner_id, user_id, base_agents):
        """Legacy method for backward compatibility."""
        if user_id and user_id.agent and user_id.salesman_as_agent and not base_agents:
            base_agents = [(0, 0, self._prepare_agent_vals(user_id))]

        team_agents = self._prepare_agents_team_vals_partner(partner_id, team)

        if team.only_team_agents:
            return team_agents

        existing_agents = {agent[2]["agent_id"]: agent for agent in base_agents}

        for team_agent in team_agents:
            agent_id = team_agent[2]["agent_id"]
            if agent_id in existing_agents:
                existing_agents[agent_id][2]["commission_id"] = team_agent[2][
                    "commission_id"
                ]
            else:
                base_agents.append(team_agent)

        return base_agents

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
