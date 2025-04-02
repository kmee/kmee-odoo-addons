# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_mercado_pago.const import SUPPORTED_CURRENCIES

from ..utils.cypher import AESCipher


_logger = logging.getLogger(__name__)

BASE_URL = "https://dev.pinbank.com.br/services/api"
AUTH_ENDPOINT = "/token"
BOLETO_PINBANK = "boleto_pinbank"


class Paymentprovider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[(BOLETO_PINBANK, "Boleto PinBank")], ondelete={BOLETO_PINBANK: 'set default'}
    )

    pinbank_user = fields.Char(string="Usuário PinBank", required_if_provider=BOLETO_PINBANK)
    pinbank_secret = fields.Char(string="Senha PinBank", required_if_provider=BOLETO_PINBANK)
    pinbank_channel = fields.Integer(string="Código Canal PinBank", required_if_provider=BOLETO_PINBANK)
    pinbank_client = fields.Integer(string="Código Cliente PinBank", required_if_provider=BOLETO_PINBANK)

    # === BUSINESS METHODS === #

    def _boleto_pinbank_save_token(self, token, expire_in):
        self.env['ir.config_parameter'].sudo().set_param('pinbank.token', token)

        if expire_in:
            expiration = datetime.now() + timedelta(seconds=expire_in)
            self.pinkbank_token_expiration = expiration

    def _boleto_pinbank_check_existing_token(self):
        if not self.token_expiration_date:
            return False

        if self.token_expiration_date < datetime.now():
            return False

        token = IrParamSudo.get_param('pinbank.token')
        return token

    def _boleto_pinbank_get_token(self):
        """ Get the Pin Bank access token

        :return (str): access_token
        """
        token = self._boleto_pinbank_check_existing_token()
        if token:
            return token

        url = BASE_URL + AUTH_ENDPOINT
        payload = {
            "username": self.pinbank_user,
            "password": self.pinbank_secret,
            "grant_type": "password",
        }
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        token = response.json().get("access_token")
        expire_in = response.json().get("expire_in")
        self._boleto_pinbank_save_token(token, expire_in)
        return token

    def _boleto_pinbank_get_headers(self):
        token = self._boleto_pinbank_get_token()
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer {token}".format(token=token),
            "RequestOrigin": "5",
            "UserName": self.pinbank_user,
        }
    
    def _get_default_vals(self, acquirer_reference):
        return {
            "CodigoCanal": self.pinbank_channel,
            "CodigoCliente": self.pinbank_client,
            "NossoNumero": acquirer_reference,
        }

    def _boleto_pinbank_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to PinBank API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = urls.url_join(BASE_URL, endpoint)
        headers = self._boleto_pinbank_get_headers()
        cypher = AESCipher(key=self.pinbank_secret.encode("utf-8"))
        payload = cypher.encrypt(payload)
        try:
            response = requests.request(url, method=method, params=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                )
                response_content = response.json()
                error_message = validation_data.get('Message', '')
                raise ValidationError("Pin Bank: " + _(
                    "The communication with the API failed. Pin Bank gave us the following "
                    "information: '%s'", error_message
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Pin Bank: " + _("Could not establish the connection to the API.")
            )
        return cypher.decrypt(response.json().get("Data", ""))
