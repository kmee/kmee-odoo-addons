from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_boleto_inter_transactions(self):
        """Devolve as transações do Inter com boleto emitido para o pedido.

        :return: As transações com boleto.
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()
        return self.transaction_ids.filtered(
            lambda t: t.provider_code == "inter" and t.boleto_pdf
        ).sorted("due_date")
