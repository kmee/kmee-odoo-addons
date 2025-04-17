from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def generate_boletos(self):
        payment_provider_id = self.payment_mode_id.payment_provider_id

        if payment_provider_id.code == "boleto_pinbank":
            self._create_boletos_pinbank()

        return super().generate_boletos()

    def _create_boletos_pinbank(self):
        provider = self.payment_mode_id.payment_provider_id

        if not provider:
            raise UserError(_("Configure o modo de pagamento do Boleto PinBank"))

        index = 0
        for moveline in self.due_line_ids.filtered(lambda x: not x.reconciled):
            index += 1
            payment_transaction_data = self._prepare_payment_transaction(
                moveline, index
            )
            transaction = self.env["payment.transaction"].create(
                payment_transaction_data
            )
            transaction.generate_boleto()

    def _prepare_payment_transaction(self, moveline, index):
        provider = self.payment_mode_id.payment_provider_id
        return {
            "is_boleto_payment": True,
            "reference": f"{moveline.name}/{index}",
            "provider_id": provider.id,
            "amount": round(moveline.amount_residual, 2),
            "currency_id": moveline.move_id.currency_id.id,
            "partner_id": moveline.partner_id.id,
            "due_date": moveline.date_maturity,
            "invoice_ids": [(6, 0, self.ids)],
            "boleto_penalty": self.payment_mode_id.payment_boleto_penalty,
            "boleto_interest": self.payment_mode_id.payment_boleto_interest,
            "boleto_instructions": self.payment_mode_id.payment_boleto_instructions,
        }
