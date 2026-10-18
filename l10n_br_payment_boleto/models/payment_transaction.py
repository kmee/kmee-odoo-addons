# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PaymentTransaction(models.Model):

    _inherit = "payment.transaction"

    is_boleto_payment = fields.Boolean("Is boleto payment")
    due_date = fields.Date()
    our_number = fields.Char()
    digitable_line = fields.Char()
    barcode = fields.Char()
    boleto_pdf = fields.Binary(string="Boleto PDF")
    boleto_penalty = fields.Float(
        string="Penalty",
        help=(
            "Penalty fee for overdue payments. "
            "This value will be added to the total amount of the invoice."
        ),
    )
    boleto_interest = fields.Float(
        string="Interest",
        help=(
            "Interest fee for overdue payments. "
            "This value will be added to the total amount of the invoice."
        ),
    )
    boleto_instructions = fields.Text(
        string="Instructions",
        help=(
            "Instructions to be printed on the boleto. "
            "This field is used to provide additional information to the payer."
        ),
    )
    provider_technical_info = fields.Text(
        string="Technical Information",
        help="Technical information about the payment transaction.",
    )

    def generate_boleto(self):
        raise NotImplementedError

    def _update_transaction_with_boleto_info(self, boleto_response):
        raise NotImplementedError

    def _prepare_transaction_boleto_info(self, boleto_response):
        return {
            "our_number": "",
            "digitable_line": "",
            "barcode": "",
            "boleto_pdf": "",
        }
