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
        """Emite um boleto por parcela em aberto.

        A parcela que ja tem boleto vivo fica de fora, para gerar de novo nao
        cobrar o cliente em dobro. O indice segue a posicao da parcela entre
        todas as parcelas da fatura, e nao entre as abertas, para nao mudar
        quando uma parcela e paga.
        """
        provider = self.payment_mode_id.payment_provider_id

        if not provider:
            raise UserError(_("Configure o modo de pagamento do Boleto PinBank"))

        installments = self.due_line_ids.sorted(lambda x: (x.date_maturity, x.id))
        for index, moveline in enumerate(installments, start=1):
            if moveline.reconciled or self._boleto_get_active_transactions(moveline):
                continue
            payment_transaction_data = self._prepare_payment_transaction(
                moveline, index
            )
            transaction = self.env["payment.transaction"].create(
                payment_transaction_data
            )
            transaction.generate_boleto()

    def _prepare_payment_transaction(self, moveline, index):
        provider = self.payment_mode_id.payment_provider_id
        # A referencia e unica no payment.transaction: um boleto que falhou e e
        # emitido de novo ganha um sufixo em vez de estourar a restricao.
        reference = self.env["payment.transaction"]._compute_reference(
            provider.code, prefix=f"{moveline.name or self.name}/{index}"
        )
        return {
            "is_boleto_payment": True,
            "reference": reference,
            "provider_id": provider.id,
            "amount": round(moveline.amount_residual, 2),
            "currency_id": moveline.move_id.currency_id.id,
            "partner_id": moveline.partner_id.id,
            "due_date": moveline.date_maturity,
            "invoice_ids": [(6, 0, self.ids)],
            "move_line_id": moveline.id,
            "boleto_penalty": self.payment_mode_id.payment_boleto_penalty,
            "boleto_interest": self.payment_mode_id.payment_boleto_interest,
            "boleto_instructions": self.payment_mode_id.payment_boleto_instructions,
        }
