from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def web_save(self, vals, specification, next_id=None):
        # Saves coming from the web client are user edits: opt in to the
        # due date guard (internal flows call write() directly).
        return super(
            AccountMove, self.with_context(maturity_edit_check=True)
        ).web_save(vals, specification, next_id=next_id)
