from odoo import api, models


class AccountMoveLineCommission(models.Model):
    _inherit = "account.move.line.commission"

    @api.constrains("agent_id", "amount")
    def _check_settle_integrity(self):
        """Override to allow modification of settled lines for period commission"""
        return True
