from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # Para inserir as opções de parcelamento no template:

    # <select name="installment_number" id="installment" required="required">
    #     <option value="1">1x sem juros</option>
    #     <t t-foreach="tx.provider_id.get_installment_options(tx.amount)" t-as="opt">
    #         <option t-att-value="opt['value']">
    #             <t t-esc="opt['label']"/>
    #         </option>
    #     </t>
    # </select>

    # e para inserir o número de parcelas é só passar o campo
    # installmente_number na chamada do seu post do pagamento

    def get_installment_options(self, amount):
        """Retorna lista de dicts [{label, value}] com as opções de parcelamento"""
        self.ensure_one()
        options = []

        # sempre 1x sem juros como default
        options.append(
            {
                "label": f"1x de R$ {amount:.2f} sem juros",
                "value": "1",  # número fixo
            }
        )

        terms = self.env["account.payment.term"].search(
            [
                ("is_installment", "=", True),
                ("provider_id", "=", self.id),
            ]
        )

        # ordenar pelo número de parcelas
        terms = sorted(terms, key=lambda t: len(t.line_ids))

        for term in terms:
            n_installments = len(term.line_ids) or 1
            labels = term.compute_installment_options(amount)
            for lbl in labels:
                options.append(
                    {
                        "label": lbl,
                        "value": str(n_installments),
                    }
                )

        return options
