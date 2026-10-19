from odoo import _, models
from odoo.exceptions import UserError

# Estados em que o boleto da parcela ainda vale no banco.
BOLETO_ACTIVE_STATES = ("draft", "pending", "authorized", "done")


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.payment_mode_id.generate_boletos_on_invoice:
                move.generate_boletos()

        return res

    def generate_boletos(self):
        self.ensure_one()
        if not self.payment_mode_id.payment_provider_id:
            raise UserError(
                _(
                    "Could not generate the boletos. No payment provider is "
                    "configured for the selected payment method"
                )
            )

    def _boleto_get_active_transactions(self, moveline):
        """Return the live boleto transactions of an installment.

        Generating the boletos again must not charge the same installment
        twice: an installment with a transaction in a live state is skipped.
        A transaction in error or canceled does not count, so the boleto can
        be generated again.

        :param recordset moveline: The installment, as an `account.move.line`.
        :return: The live transactions of the installment.
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()
        return self.transaction_ids.filtered(
            lambda t: t.move_line_id == moveline and t.state in BOLETO_ACTIVE_STATES
        )
