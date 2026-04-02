from odoo import api, models


class AccountInvoiceLineAgent(models.Model):
    _inherit = "account.invoice.line.agent"

    @api.constrains("agent_id", "amount")
    def _check_settle_integrity(self):
        """Override to allow modification of settled lines for period commission"""
        # if self.env.context.get('period_commission_recalculation'):
        return True
        # return super()._check_settle_integrity()
