from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("restrict_mode_hash_table", "state")
    def _compute_show_reset_to_draft_button(self):
        super(AccountMove, self)._compute_show_reset_to_draft_button()
        for move in self:
            if self.env.user.has_group(
                "account_back2draft_security.group_user_hide_back_to_draft_button"
            ):
                move.show_reset_to_draft_button = False
        return
