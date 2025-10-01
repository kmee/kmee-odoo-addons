from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    is_installment = fields.Boolean(
        string="Permitir Parcelamento",
        help="Indica se este termo de pagamento permite parcelamento.",
        default=False,
    )

    provider_id = fields.Many2one(
        comodel_name="payment.provider",
        string="Provedor de Pagamento",
        help="Provedor de pagamento utilizado para processar os pagamentos com parcelamento.",
        ondelete="set null",
    )

    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Termo de Pagamento Pai",
        help="Termo de pagamento pai associado a este termo de pagamento.",
        ondelete="set null",
    )

    installment_rate = fields.Float(
        string="Taxa de Parcelamento (%)",
        help="Taxa de parcelamento aplicada sobre o valor total da fatura.",
        default=0.0,
    )

    installment_type = fields.Selection(
        selection=[
            ("simple", "Juros Simples"),
            ("compose", "Juros Compostos"),
        ],
        string="Tipo de Juros",
        help="Tipo de juros aplicado no parcelamento.",
        default="simple",
        required=True,
    )

    def compute_installment_options(self, amount):
        """Retorna lista de strings com descrições tipo '3x de R$ 100,00'"""
        results = []
        n = len(self.line_ids) or 1
        r = self.installment_rate / 100.0

        if not self.is_installment or n <= 1:
            return [f"1x de R$ {amount:.2f}"]

        if self.installment_type == "simple":
            total = amount * (1 + r * (n - 1))
            per = total / n
        else:
            pmt = amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
            per = pmt

        if self.installment_rate > 0:
            results.append(f"{n}x de R$ {per:.2f} com juros")
        else:
            results.append(f"{n}x de R$ {per:.2f} sem juros")

        return results
