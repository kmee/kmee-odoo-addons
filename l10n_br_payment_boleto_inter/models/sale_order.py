from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_print_boleto(self):
        self.ensure_one()

        # Pega a transação vinculada ao pedido
        tx = self.transaction_ids.filtered(lambda t: t.provider_code == "inter")[:1]

        if not tx or not tx.boleto_pdf:
            raise UserError(_("Boleto não disponível para este pedido de venda."))

        return {
            "type": "ir.actions.act_url",
            "url": f"/payment/boleto/{tx.id}?download=true",
            "target": "self",
        }
