from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_boleto_inter_transactions(self):
        """Devolve as transações do Inter com boleto emitido para a fatura.

        Uma fatura parcelada tem uma transação por vencimento, e o relatório
        junta todos os boletos num arquivo só.

        :return: As transações com boleto.
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()
        return self.transaction_ids.filtered(
            lambda t: t.provider_code == "inter" and t.boleto_pdf
        ).sorted("due_date")

    def generate_boletos(self):
        """Gera boletos apenas para transações com provider Inter"""
        payment_provider_id = self.payment_mode_id.payment_provider_id

        if payment_provider_id and payment_provider_id.code == "inter":
            self._create_boletos_inter()

        return super().generate_boletos()

    def _create_boletos_inter(self):
        """Cria transactions para cada linha de vencimento não conciliada"""
        provider = self.payment_mode_id.payment_provider_id
        if not provider:
            raise UserError(_("Configure o modo de pagamento do Boleto Inter"))

        for index, moveline in enumerate(
            self.due_line_ids.filtered(lambda x: not x.reconciled), start=1
        ):
            transaction_vals = self._prepare_boleto_payload(moveline, index)
            transaction = self.env["payment.transaction"].create(transaction_vals)
            transaction.generate_boleto()

    def _prepare_boleto_payload(self, moveline, index):
        """Prepara os campos do payment.transaction"""
        provider = self.payment_mode_id.payment_provider_id
        if not provider:
            raise UserError(_("Configure o modo de pagamento do Boleto Inter"))

        return {
            "partner_id": moveline.partner_id.id,
            "provider_id": provider.id,
            "is_boleto_payment": True,
            "amount": moveline.amount_residual,
            "currency_id": moveline.move_id.currency_id.id,
            "due_date": moveline.date_maturity,
            "our_number": f"{moveline.name}/{index}",
            "boleto_penalty": self.payment_mode_id.payment_boleto_penalty or 0.0,
            "boleto_interest": self.payment_mode_id.payment_boleto_interest or 0.0,
            "boleto_instructions": self.payment_mode_id.payment_boleto_instructions
            or "",
            "invoice_ids": [(6, 0, self.ids)],
        }
