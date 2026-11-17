from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_move_action_context(self):
        # The dashboard hard-codes view_no_maturity for miscellaneous journals;
        # drop it so the Due Date column stays available.
        ctx = super()._get_move_action_context()
        ctx.pop("view_no_maturity", None)
        return ctx
