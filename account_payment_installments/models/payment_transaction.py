from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    payment_term_id = fields.Many2one(
        "account.payment.term", string="Condição de Parcelamento"
    )

    installment_number = fields.Integer(
        string="Número de Parcelas",
        default=1,
        help="Quantidade de parcelas escolhida pelo cliente.",
    )

    def get_installment_options(self):
        """Retorna lista de dicts [{label, value}] para usar no template"""
        self.ensure_one()
        terms = self.env["account.payment.term"].search(
            [
                ("is_installment", "=", True),
                ("provider_id", "=", self.provider_id.id),
            ]
        )
        options = []
        for term in terms:
            labels = term.compute_installment_options(self.amount)
            for lbl in labels:
                options.append({"label": lbl, "value": term.id})
        return options
