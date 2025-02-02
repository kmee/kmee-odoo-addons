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
        if not agent_team_ids:
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

    def _compute_agents_with_team(self, team, partner_id, base_agents):
        """Generalized method for merging agents from sales/invoice teams."""
        if not (partner_id and team):
            return base_agents

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
