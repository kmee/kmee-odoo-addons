# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleCommissionTeamMixin(models.AbstractModel):

    _name = "sale.commission.team.mixin"
    _description = "Agent Team Mixin"

    sequence = fields.Integer(
        string="Sequence",
    )

    team_id = fields.Many2one(
        comodel_name="crm.team",
        required=True,
        string="Sales Team",
    )

    agent_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        string="Agent",
        domain="[('agent', '=', True)]",
    )

    commission_id = fields.Many2one(
        comodel_name="sale.commission",
        required=True,
        string="Commission",
        help="This is the default commission used in the sales where this "
        "agent is assigned. It can be changed on each operation if "
        "needed.",
    )
