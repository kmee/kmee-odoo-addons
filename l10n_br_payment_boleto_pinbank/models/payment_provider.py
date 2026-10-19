import json
import logging
from datetime import datetime, timedelta

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from ..utils.cypher import AESCipher

_logger = logging.getLogger(__name__)

AUTH_ENDPOINT = "/token"
BOLETO_PINBANK = "boleto_pinbank"

BASE_URL = {
    "enabled": "https://pinbank.com.br/services/api",
    "test": "https://dev.pinbank.com.br/services/api",
}


class Paymentprovider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[(BOLETO_PINBANK, "Boleto PinBank")],
        ondelete={BOLETO_PINBANK: "set default"},
    )

    pinbank_user = fields.Char(
        string="Usuário PinBank", required_if_provider=BOLETO_PINBANK
    )
    pinbank_secret = fields.Char(
        string="Senha PinBank", required_if_provider=BOLETO_PINBANK
    )
    pinbank_channel = fields.Integer(
        string="Código Canal PinBank", required_if_provider=BOLETO_PINBANK
    )
    pinbank_client = fields.Integer(
        string="Código Cliente PinBank", required_if_provider=BOLETO_PINBANK
    )

    pinbank_request_origin = fields.Char(
        string="Código Origem Requisição PinBank",
        required_if_provider=BOLETO_PINBANK,
    )

    # === BUSINESS METHODS === #

    def _boleto_pinbank_token_param_names(self):
        """Devolve as chaves usadas para guardar o token do provider.

        O token e emitido por conta: guardar um unico token para toda a base faz
        duas contas PinBank, ou o ambiente de teste e o de producao, usarem o
        token uma da outra.

        :return: As chaves do token e da sua expiracao.
        :rtype: tuple
        """
        self.ensure_one()
        return (
            f"pinbank.token.{self.id}",
            f"pinbank.token.expiration.{self.id}",
        )

    def _boleto_pinbank_save_token(self, token, expire_in):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        token_key, expiration_key = self._boleto_pinbank_token_param_names()
        IrParamSudo.set_param(token_key, token)

        if expire_in:
            expiration = datetime.now() + timedelta(seconds=int(expire_in))
            IrParamSudo.set_param(expiration_key, expiration.isoformat())

    def _boleto_pinbank_check_existing_token(self):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        token_key, expiration_key = self._boleto_pinbank_token_param_names()
        token_expiration = IrParamSudo.get_param(expiration_key)
        if not token_expiration:
            return False

        # O parametro volta como texto: comparar direto com datetime estoura.
        try:
            token_expiration = datetime.fromisoformat(token_expiration)
        except ValueError:
            return False
        if token_expiration < datetime.now():
            return False

        return IrParamSudo.get_param(token_key)

    def _boleto_pinbank_get_token(self):
        """Get the Pin Bank access token

        :return (str): access_token
        """
        token = self._boleto_pinbank_check_existing_token()
        if token:
            return token

        url = BASE_URL.get(self.state, "test") + AUTH_ENDPOINT
        payload = {
            "username": self.pinbank_user,
            "password": self.pinbank_secret,
            "grant_type": "password",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                _("Pin Bank: Could not establish the connection to the API.")
            ) from None

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.exception(
                "Invalid API request at %s",
                url,
            )
            response_content = response.json()
            error_message = response_content.get("Message", "")
            raise ValidationError(
                _(
                    "Pin Bank: The communication with the API failed. Pin Bank "
                    "gave us the following information: '%s'",
                    error_message,
                )
            ) from requests.exceptions.HTTPError

        token = response.json().get("access_token")
        expire_in = response.json().get("expire_in")
        self._boleto_pinbank_save_token(token, expire_in)
        return token

    def _boleto_pinbank_get_headers(self):
        token = self._boleto_pinbank_get_token()
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "RequestOrigin": self.pinbank_request_origin,
            "UserName": self.pinbank_user,
        }

    def _get_default_vals(self, acquirer_reference):
        return {
            "CodigoCanal": self.pinbank_channel,
            "CodigoCliente": self.pinbank_client,
            "NossoNumero": acquirer_reference,
        }

    def _boleto_pinbank_make_request(
        self,
        endpoint,
        headers=None,
        payload=None,
        encrypted_endpoint=True,
        method="POST",
    ):
        """Make a request to PinBank API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = BASE_URL.get(self.state, "test") + endpoint

        if not headers:
            headers = self._boleto_pinbank_get_headers()

        cypher = AESCipher(key=self.pinbank_secret.encode("utf-8"))
        if encrypted_endpoint:
            payload = json.dumps(payload, ensure_ascii=False)
            payload = cypher.encrypt(payload).decode()
            payload = {"Data": {"Json": payload}}

        try:
            response = requests.request(
                url=url, method=method, json=payload, headers=headers, timeout=10
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s",
                    url,
                )
                response_content = response.json()
                error_message = response_content.get("Message", "")
                raise ValidationError(
                    _(
                        "Pin Bank: The communication with the API failed. Pin "
                        "Bank gave us the following information: '%s'",
                        error_message,
                    )
                ) from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                _("Pin Bank: Could not establish the connection to the API.")
            ) from None

        if not encrypted_endpoint:
            return response.json()

        response_data = response.json().get("Data", {})
        if not response_data:
            error_msg = "Pin Bank: " + response.json().get("Message", "")
            _logger.exception(error_msg)
            raise ValidationError(error_msg)

        encrypted_json = response_data.get("Json", "")
        return json.loads(cypher.decrypt(encrypted_json))

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        return self.filtered(lambda p: p.code == BOLETO_PINBANK).update(
            {
                "support_fees": True,
                "support_manual_capture": True,
                "support_refund": "full_only",
                "support_tokenization": True,
            }
        )
