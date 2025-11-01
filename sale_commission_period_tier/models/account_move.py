from odoo import api, models


class AccountMoveLineAgent(models.Model):
    _inherit = "account.move.line.agent"

    @api.constrains("agent_id", "amount")
    def _check_settle_integrity(self):
        """Allow settled lines update during period commission recalculation."""
        if self.env.context.get("period_commission_recalculation"):
            return
        super()._check_settle_integrity()
