# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from datetime import datetime

from werkzeug.urls import url_encode, url_join

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.l10n_br_pinbank.controllers.main import PinBankController
from odoo.addons.phone_validation.tools.phone_validation import phone_sanitize_numbers

from .const import PAYMENT_STATUS_MAPPING


_logger = logging.getLogger(__name__)

GERAR_BOLETO_ENDPOINT = "/CashIn/GerarBoletoEncrypted"
CANCELAR_BOLETO_ENDPOINT = "/CashIn/SolicitarBaixaBoletoEncrypted"
CONSULTAR_BOLETO_ENDPOINT = "/CashIn/ConsultarBoletoEncrypted"


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return pinbank specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'boleto_pinbank':
            return res

        # Initiate the payment and retrieve the related order id.
        payload = self._boleto_pinbank_prepare_order_request_payload()
        _logger.info(
            f"Payload of '{GERAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        order_data = self.provider_id._boleto_pinbank_make_request(endpoint=GERAR_BOLETO_ENDPOINT, payload=payload)
        _logger.info(
            f"Response of '{GERAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_data)
        )

        # Initiate the payment
        base_url = self.provider_id.get_base_url()
        return_url_params = {'reference': self.reference}

        rendering_values = {
            'name': self.company_id.name,
            'description': self.reference,
            'company_logo': url_join(base_url, f'web/image/res.company/{self.company_id.id}/logo'),
            'order_id': order_data.get("Data", {}).get("NossoNumero"),
            'amount': self.amount,
            'currency': self.currency_id.name,
            'partner_name': self.partner_name,
            'partner_email': self.partner_email,
            'return_url': url_join(
                base_url, f'{PinBankController._return_url}?{url_encode(return_url_params)}'
            ),
        }
        return rendering_values

    def _boleto_pinbank_prepare_order_request_payload(self):
        """ Create the payload for the order request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """

        return {
            "Data": {
                "CodigoCanal": self.provider_id.pinbank_channel,
                "CodigoCliente": self.provider_id.pinbank_client,
                "DataVencimento": datetime.now().date().strftime("yyyyMMdd"),
                "Valor": self.amount,
                "Email": self.partner_email,
                "DadosSacado": {
                    "CpfCnpj": re.sub("[^0-9]", "", self.partner_id.l10n_br_cnpj_cpf),
                    "Nome": self.partner_id.legal_name or partner_id.name,
                    "Endereco": self.partner_id.street,
                    "Bairro": self.partner_id.l10n_br_district,
                    "Cidade": self.partner_id.city_id.name,
                    "Cep": re.sub("[^0-9]", "", self.partner_id.zip),
                    "Uf": self.partner_id.state_id.code,
                },
                "IdentificadorCliente": self.reference,
                "RetornarBase64": True,
                "Instrucoes": "Não imprimir",
                **({
                    "Juros": {
                        "Valor": 0
                    }
                } if False else {}),
                **({
                    "Multa": {
                        "Valor": 0
                    }
                } if False else {}),
            }
        }

        return payload

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of `payment` to send a refund request to PinBank.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'boleto_pinbank':
            return refund_tx

        # Make the refund request to PinBank.
        payload = {
            "CodigoCanal": self.provider_id.pinbank_channel,
            "CodigoCliente": self.provider_id.pinbank_client,
            "NossoNumero": self.reference,
        }
        _logger.info(
            f"Payload of '{CANCELAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = refund_tx.provider_id._boleto_pinbank_make_request(
            CANCELAR_BOLETO_ENDPOINT, payload=payload
        )
        _logger.info(
            f"Response of '{CANCELAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        response_content.update(entity_type='refund')
        refund_tx._handle_notification_data('boleto_pinbank', response_content)

        return refund_tx

    def _send_capture_request(self):
        """ Override of `payment` to send a capture request to PinBank.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != 'boleto_pinbank':
            return

        payload = {
            "CodigoCanal": self.provider_id.pinbank_channel,
            "CodigoCliente": self.provider_id.pinbank_client,
            "NossoNumero": self.reference,
        }
        _logger.info(
            f"Payload of '{CONSULTAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = self.provider_id._boleto_pinbank_make_request(
            CONSULTAR_BOLETO_ENDPOINT, payload=payload
        )
        _logger.info(
            f"Response of '{CONSULTAR_BOLETO_ENDPOINT}' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )

        # Handle the capture request response.
        self._handle_notification_data('boleto_pinbank', response_content)

    def _send_void_request(self):
        """ Override of `payment` to explain that it is impossible to void a Pinbank transaction.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'boleto_pinbank':
            return

        raise UserError(_("Transactions processed by PinBank can't be manually voided from Odoo."))

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on pinbank data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'boleto_pinbank' or len(tx) == 1:
            return tx

        entity_type = notification_data.get('entity_type', 'payment')
        if entity_type == 'payment':
            reference = notification_data.get('Data', {}).get('NossoNumero', '')
            if not reference:
                raise ValidationError("Boleto PinBank: " + _("Received data with missing reference."))
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'boleto_pinbank')])
        else:  # 'refund'
            reference = notification_data.get('Data', {}).get('NossoNumero', '')
            if reference:  # The refund was initiated from Odoo.
                tx = self.search([('reference', '=', reference), ('provider_code', '=', 'boleto_pinbank')])
            else:  # The refund was initiated from PinBank.
                # Find the source transaction based on its provider reference.
                source_tx = self.search([
                    ('provider_reference', '=', notification_data['payment_id']),
                    ('provider_code', '=', 'boleto_pinbank'),
                ])
                if source_tx:
                    # Manually create a refund transaction with a new reference.
                    tx = self._boleto_pinbank_create_refund_tx_from_notification_data(
                        source_tx, notification_data
                    )
                else:  # The refund was initiated for an unknown source transaction.
                    pass  # Don't do anything with the refund notification.
        if not tx:
            raise ValidationError(
                "Pinbank: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _boleto_pinbank_create_refund_tx_from_notification_data(self, source_tx, notification_data):
        """ Create a refund transaction based on Pinbank data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset.
        :param dict notification_data: The notification data sent by the provider.
        :return: The newly created refund transaction.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        """
        refund_provider_reference = notification_data.get('Data', {}).get('NossoNumero', '')
        return source_tx._create_refund_transaction(
            amount_to_refund=source_tx.amount, provider_reference=refund_provider_reference
        )

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on PinBank data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'boleto_pinbank':
            return

        payload = {
            "CodigoCanal": self.provider_id.pinbank_channel,
            "CodigoCliente": self.provider_id.pinbank_client,
            "NossoNumero": self.reference,
        }
        entity_data = self.provider_id._boleto_pinbank_make_request(
            CONSULTAR_BOLETO_ENDPOINT, payload=payload
        ).get('Data', {})

        entity_id = entity_data.get("NossoNumero", False)
        if not entity_id:
            raise ValidationError("PinBank: " + _("Received data with missing entity id."))
        self.provider_reference = entity_id

        entity_status = entity_data.get("Status")
        if not entity_status:
            raise ValidationError("PinBank: " + _("Received data with missing status."))

        if entity_status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif entity_status in PAYMENT_STATUS_MAPPING['authorized']:
            self._set_authorized()
        elif entity_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif entity_status in PAYMENT_STATUS_MAPPING['error']:
            _logger.warning(
                "The transaction with reference %s underwent an error. Reason: %s",
                self.reference, entity_data.get('ValidationData', {}).get("Errors")
            )
            self._set_error(
                _("An error occurred during the processing of your payment. Please try again.")
            )
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s",
                self.reference, entity_status
            )
            self._set_error(
                "PinBank: " + _("Received data with invalid status: %s", entity_status)
            )
