from odoo import api, models


class AccountMoveLineAgent(models.Model):
    _inherit = "account.move.line.agent"

    @api.constrains("agent_id", "amount")
    def _check_settle_integrity(self):
        """Allow recalculation context to bypass settlement integrity checks."""
        if not self.env.context.get("period_commission_recalculation"):
            super()._check_settle_integrity()
