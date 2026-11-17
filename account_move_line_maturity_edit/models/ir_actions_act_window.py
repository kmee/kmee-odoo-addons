import ast

from odoo import api, models


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    @api.model
    def _maturity_edit_fix_action_context(self):
        """Remove only the 'view_no_maturity' key from the Journal Entries
        action context. Called from data on every install/update of this
        module; note that ``-u account`` alone restores the key until this
        module is updated again."""
        action = self.env.ref("account.action_move_journal_line", False)
        if not action:
            return
        try:
            ctx = ast.literal_eval(action.context or "{}")
        except (ValueError, SyntaxError):
            return
        if isinstance(ctx, dict) and "view_no_maturity" in ctx:
            ctx.pop("view_no_maturity")
            action.context = repr(ctx)
