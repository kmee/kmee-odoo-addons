from odoo import api, models


class AccountMoveLineCommission(models.Model):
    _inherit = "account.invoice.line.agent"

    @api.constrains("agent_id", "amount")
    def _check_settle_integrity(self):
        """Override to allow modification of settled lines for period commission"""
        return True
