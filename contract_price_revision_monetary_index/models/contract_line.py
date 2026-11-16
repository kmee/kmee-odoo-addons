# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    revision_index_id = fields.Many2one(
        comodel_name="monetary.index",
        string="Revised by Index",
        copy=False,
        readonly=True,
    )
    revision_period_start = fields.Date(
        string="Index Period Start", copy=False, readonly=True
    )
    revision_period_end = fields.Date(
        string="Index Period End", copy=False, readonly=True
    )
    revision_factor = fields.Float(
        string="Index Factor", digits=(16, 8), copy=False, readonly=True
    )
    revision_percent = fields.Float(
        string="Index Variation Applied (%)",
        digits=(16, 4),
        copy=False,
        readonly=True,
    )
