from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_match_or_create_picking(self):
        self.ensure_one()
        wizard = self.env["account.move.match.picking"].create(
            {"account_move_id": self.id}
        )
        wizard._compute_candidate_pickings()
        return {
            "type": "ir.actions.act_window",
            "name": "Match or Create Pickings",
            "res_model": "account.move.match.picking",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
