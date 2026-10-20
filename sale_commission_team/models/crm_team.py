# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmTeam(models.Model):

    _inherit = "crm.team"

    commission_rule_ids = fields.Many2many(
        "commission.rule",
        "crm_team_commission_rule_rel",
        "team_id",
        "rule_id",
        string="Commission Rules",
        domain=[("active", "=", True)],
    )

    # Deprecated field
    only_team_agents = fields.Boolean()

    agent_ids = fields.One2many(
        comodel_name="crm.team.agent",
        inverse_name="team_id",
    )
