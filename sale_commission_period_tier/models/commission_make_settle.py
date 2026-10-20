# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class CommissionMakeSettle(models.TransientModel):
    _inherit = "commission.make.settle"

    def action_settle(self):
        """Apply the period tiers on the settlements created or updated."""
        result = super().action_settle()
        if result and result.get("domain"):
            settlement_ids = result["domain"][0][2]
            self.env["commission.settlement"].browse(
                settlement_ids
            ).recalculate_period_commission()
        return result
