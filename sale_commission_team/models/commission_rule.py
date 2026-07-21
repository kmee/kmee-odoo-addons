# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CommissionRule(models.Model):
    _name = "commission.rule"
    _description = "Commission Rule"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        [
            ("team", "Team Commission"),
            ("team_partner", "Team and Partner Commission"),
            ("partner", "Partner Commission"),
            ("salesman", "Salesman Commission"),
        ],
        required=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
