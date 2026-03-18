from odoo import fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    van_session_id = fields.Many2one("van.session", index=True)

    def _validate_session(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        res = super()._validate_session(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )
        if self.van_session_id:
            self.van_session_id._on_pos_session_closed()
        return res

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        res = super().close_session_from_ui(bank_payment_method_diff_pairs)
        if self.van_session_id and isinstance(res, dict) and res.get("successful"):
            res["van_session_id"] = self.van_session_id.id
        return res
