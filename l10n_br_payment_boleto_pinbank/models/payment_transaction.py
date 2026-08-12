import logging
import pprint
import re

from werkzeug.urls import url_encode, url_join

from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..controllers.main import PinBankController

_logger = logging.getLogger(__name__)

GERAR_BOLETO_ENDPOINT = "/CashIn/GerarBoletoEncrypted"
CANCELAR_BOLETO_ENDPOINT = "/CashIn/SolicitarBaixaBoletoEncrypted"
CONSULTAR_BOLETO_ENDPOINT = "/CashIn/ConsultarBoletoEncrypted"

# Chaves que carregam dados pessoais do sacado e nao vao para o log.
PERSONAL_DATA_KEYS = frozenset(
    {
        "cpfcnpj",
        "nome",
        "email",
        "endereco",
        "bairro",
        "cep",
        "dadossacado",
        "base64",
    }
)

STATE_MAPPING = {
    "PENDENTE": "pending",
    "REGISTRADO": "authorized",
}


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def action_generate_boleto(self):
        self._set_pending(
            f"Transaction with reference {self.reference} starting to generate boleto"
        )
        self.generate_boleto()

    def generate_boleto(self):
        if self.provider_id.code == "boleto_pinbank":
            return self._send_payment_request()

        super().generate_boleto()

    def _send_payment_request(self):
        # Initiate the payment and retrieve the related order id.
        res = super()._send_payment_request()

        if self.provider_id.code != "boleto_pinbank":
            return res

        payload = self._boleto_pinbank_prepare_order_request_payload()

        response_content = self.provider_id._boleto_pinbank_make_request(
            endpoint=GERAR_BOLETO_ENDPOINT, payload=payload
        )

        response_content["last_action"] = "CREATED"

        self._handle_notification_data("boleto_pinbank", response_content)
        return response_content

    def _boleto_pinbank_prepare_order_request_payload(self):
        """Create the payload for the order request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """

        return {
            "Data": {
                "CodigoCanal": self.provider_id.pinbank_channel,
                "CodigoCliente": self.provider_id.pinbank_client,
                "DataVencimento": self.due_date.strftime("%Y%m%d"),
                "Valor": int(self.amount * 100),
                "Email": self.partner_email,
                "DadosSacado": {
                    "CpfCnpj": int(re.sub("[^0-9]", "", self.partner_id.cnpj_cpf or 0)),
                    "Nome": self.partner_id.legal_name,
                    "Endereco": self.partner_id.street_name,
                    "Bairro": self.partner_id.district,
                    "Cidade": self.partner_id.city_id.name or self.partner_id.city,
                    "Cep": int(re.sub("[^0-9]", "", self.partner_id.zip or 0)),
                    "Uf": self.partner_id.state_id.code,
                },
                "RetornarBase64": True,
                "Instrucoes": self.boleto_instructions or "",
                "Juros": {"Valor": int(self.boleto_interest * 10000)},
                "Multa": {"Valor": int(self.boleto_penalty * 10000)},
            }
        }

    def _update_transaction_with_boleto_info(self, boleto_response):
        if self.provider_code == "boleto_pinbank":
            boleto_infos = self._prepare_transaction_boleto_info(boleto_response)
            self.write(boleto_infos)
            return

        return super()._update_transaction_with_boleto_info(boleto_response)

    def _prepare_transaction_boleto_info(self, boleto_response):
        if self.provider_code == "boleto_pinbank":
            boleto_info = {
                "our_number": boleto_response["Data"]["NossoNumero"],
                "digitable_line": boleto_response["Data"]["LinhaDigitavel"],
                "barcode": boleto_response["Data"]["CodigoBarras"],
            }

            boleto_pdf = boleto_response.get("Data", {}).pop("Base64", False)
            if boleto_pdf:
                boleto_info["boleto_pdf"] = boleto_pdf

            boleto_info["provider_technical_info"] = pprint.pformat(
                self._pinbank_redact(boleto_response.get("Data", {}))
            )

            return boleto_info

        return super()._prepare_transaction_boleto_info(boleto_response)

    @api.model
    def _pinbank_redact(self, data):
        """Devolve uma copia dos dados sem os dados pessoais do sacado.

        A notificacao e a resposta do PinBank trazem nome, documento e endereco
        do sacado, e o log de um gateway nao precisa deles.

        :param data: O conteudo a limpar.
        :return: A copia limpa, segura para registrar.
        """
        if isinstance(data, dict):
            return {
                key: "***"
                if str(key).replace("_", "").lower() in PERSONAL_DATA_KEYS
                else self._pinbank_redact(value)
                for key, value in data.items()
            }
        elif isinstance(data, list | tuple):
            return [self._pinbank_redact(item) for item in data]
        return data

    def _send_refund_request(self, amount_to_refund=None):
        """Override of `payment` to send a refund request to PinBank.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != "boleto_pinbank":
            return refund_tx

        # Make the refund request to PinBank.
        payload = {
            "CodigoCanal": self.provider_id.pinbank_channel,
            "CodigoCliente": self.provider_id.pinbank_client,
            "NossoNumero": self.reference,
        }

        response_content = refund_tx.provider_id._boleto_pinbank_make_request(
            CANCELAR_BOLETO_ENDPOINT, payload=payload
        )

        response_content.update(entity_type="refund")
        refund_tx._handle_notification_data("boleto_pinbank", response_content)

        return refund_tx

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to PinBank.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != "boleto_pinbank":
            return

        response_content = self._pinbank_check_boleto_status()

        # Handle the capture request response.
        self._handle_notification_data("boleto_pinbank", response_content)

    def _pinbank_check_boleto_status(self):
        payload = {
            "Data": {
                "CodigoCanal": self.provider_id.pinbank_channel,
                "CodigoCliente": self.provider_id.pinbank_client,
                "NossoNumero": self.our_number,
            }
        }
        return self.provider_id._boleto_pinbank_make_request(
            CONSULTAR_BOLETO_ENDPOINT, payload=payload
        )

    def _send_void_request(self):
        """Override of `payment` to cancel a Pinbank transaction.

        Note: self.ensure_one()

        :return: None
        """
        res = super()._send_void_request()
        if self.provider_code != "boleto_pinbank":
            return res

        payload = {
            "Data": {
                "CodigoCanal": self.provider_id.pinbank_channel,
                "CodigoCliente": self.provider_id.pinbank_client,
                "NossoNumero": self.our_number,
            }
        }

        try:
            # Attempt to cancel the boleto in PinBank.
            response_content = self.provider_id._boleto_pinbank_make_request(
                CANCELAR_BOLETO_ENDPOINT, payload=payload
            )
        except Exception as e:
            _logger.error(
                "Failed to cancel boleto transaction %s in PinBank: %s",
                self.reference,
                e,
            )
            self._set_error(
                "PinBank: " + _("Failed to cancel boleto transaction: %s", e)
            )
            return res

        response_content = self._pinbank_check_boleto_status()
        # response_content['last_action'] = 'CANCELED'

        self._handle_notification_data("boleto_pinbank", response_content)

        return res

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return pinbank specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        super()._get_specific_rendering_values(processing_values)

        boleto_data = self._generate_boleto_pinbank()

        # Initiate the payment
        base_url = self.provider_id.get_base_url()
        return_url_params = {"reference": self.reference}

        rendering_values = {
            "name": self.company_id.name,
            "description": self.reference,
            "company_logo": url_join(
                base_url, f"web/image/res.company/{self.company_id.id}/logo"
            ),
            "order_id": boleto_data.get("Data", {}).get("NossoNumero"),
            "amount": self.amount,
            "currency": self.currency_id.name,
            "partner_name": self.partner_name,
            "partner_email": self.partner_email,
            "return_url": url_join(
                base_url,
                f"{PinBankController._return_url}?{url_encode(return_url_params)}",
            ),
        }
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of `payment` to find the transaction based on pinbank data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "boleto_pinbank" or len(tx) == 1:
            return tx

        entity_type = notification_data.get("entity_type", "payment")
        if entity_type == "payment":
            reference = notification_data.get("Data", {}).get("NossoNumero", "")
            if not reference:
                raise ValidationError(
                    _("Boleto PinBank: Received data with missing reference.")
                )
            tx = self.search(
                [
                    ("reference", "=", reference),
                    ("provider_code", "=", "boleto_pinbank"),
                ]
            )
        else:  # 'refund'
            reference = notification_data.get("Data", {}).get("NossoNumero", "")
            if reference:  # The refund was initiated from Odoo.
                tx = self.search(
                    [
                        ("reference", "=", reference),
                        ("provider_code", "=", "boleto_pinbank"),
                    ]
                )
            else:  # The refund was initiated from PinBank.
                # Find the source transaction based on its provider reference.
                source_tx = self.search(
                    [
                        ("provider_reference", "=", notification_data["payment_id"]),
                        ("provider_code", "=", "boleto_pinbank"),
                    ]
                )
                if source_tx:
                    # Manually create a refund transaction with a new reference.
                    tx = self._boleto_pinbank_create_refund_tx_from_notification_data(
                        source_tx, notification_data
                    )
                else:  # The refund was initiated for an unknown source transaction.
                    pass  # Don't do anything with the refund notification.
        if not tx:
            raise ValidationError(
                _("Pinbank: No transaction found matching reference %s.", reference)
            )

        return tx

    def _boleto_pinbank_create_refund_tx_from_notification_data(
        self, source_tx, notification_data
    ):
        """Create a refund transaction based on Pinbank data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset.
        :param dict notification_data: The notification data sent by the provider.
        :return: The newly created refund transaction.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        """

        refund_provider_reference = notification_data.get("Data", {}).get(
            "NossoNumero", ""
        )
        return source_tx._create_refund_transaction(
            amount_to_refund=source_tx.amount,
            provider_reference=refund_provider_reference,
        )

    def _process_notification_data(self, notification_data):
        """Override of `payment` to process the transaction based on PinBank data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != "boleto_pinbank":
            return

        status = notification_data.get("Data", {}).get("Status", False)
        last_action = notification_data.get("last_action", False)

        if not status and not last_action:
            _logger.warning(
                "Received data for transaction with reference %s "
                "with missing status: %s",
                self.reference,
                pprint.pformat(self._pinbank_redact(notification_data)),
            )
            self._set_error("PinBank: " + _("Received data with missing status."))
            return

        if status == "PENDENTE" or last_action == "CREATED":
            self._set_pending(
                f"Transaction with reference {self.reference} is pending in PinBank"
            )
        elif status == "REGISTRADO":
            self._set_authorized(
                f"Transaction with reference {self.reference} authorized by PinBank"
            )
        elif status == "LIQUIDADO":
            self._set_done(
                f"Transaction with reference {self.reference} was paid in PinBank"
            )

        elif status == "BAIXA":
            self._set_canceled(
                f"Transaction with reference {self.reference} was settled in PinBank"
            )

        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s "
                "with invalid payment status: %s",
                self.reference,
                status,
            )
            self._set_error(
                "PinBank: " + _("Received data with invalid status: %s", status)
            )

        self._update_transaction_with_boleto_info(notification_data)

    def cron_check_for_authorized_boletos(self):
        self._check_boleto_with_status("pending")

    def cron_check_for_paid_boletos(self):
        self._check_boleto_with_status("authorized")

    def _check_boleto_with_status(self, status):
        """Check the status of the boleto transaction.

        Note: self.ensure_one()

        :return: None
        """
        transactions_to_check = self.search(
            [
                ("state", "=", status),
                ("provider_code", "=", "boleto_pinbank"),
            ]
        )

        for transaction in transactions_to_check:
            try:
                transaction._send_capture_request()
            except ValidationError as e:
                _logger.error(
                    "Failed to check the status of boleto transaction %s: %s",
                    transaction.reference,
                    e,
                )
