from odoo import models
from odoo.exceptions import ValidationError, UserError

class PaymentTransaction(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        self._create_boletos_pinbank()
        return super().action_post()

    def _create_boletos_pinbank(self):
        provider = self.env['payment.provider'].search([
            ('code', '=', 'boleto_pinbank')
        ])

        if not provider:
            raise UserError(
                'Configure o modo de pagamento do Boleto PinBank')
        for moveline in self.financial_move_line_ids.filtered(lambda x: not x.reconciled):
            transaction = self.env['payment.transaction'].create({
                    'provider_id': provider.id,
                    'amount': round(moveline.amount_residual, 2),
                    'currency_id': moveline.move_id.currency_id.id,
                    'partner_id': moveline.partner_id.id,
                    # 'date_maturity': moveline.date_maturity,
                    'invoice_ids': [(6, 0, self.ids)],
                })

            transaction._get_specific_rendering_values({})
        
