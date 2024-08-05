# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):

    _inherit = "account.move"

    contract_config_line_ids = fields.One2many(
        "account.move.line",
        "move_id",
        string="Invoice lines",
        copy=False,
        readonly=True,
        domain=[("display_type", "in", ("product", "line_section", "line_note"))],
    )
