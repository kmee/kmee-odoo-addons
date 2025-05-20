from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        if self.payment_mode_id.generate_boletos_on_invoice:
            self.generate_boletos()

        return res

    def generate_boletos(self):
        if not self.payment_mode_id.payment_provider_id:
            raise UserError(
                _(
                    "Could not generate the boletos. No payment provider is "
                    "configured for the selected payment method"
                )
            )
