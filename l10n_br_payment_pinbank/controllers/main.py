import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PinBankController(http.Controller):
    _return_url = "/payment/pinbank/return"

    @http.route(
        _return_url,
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def pinbank_return_from_checkout(self, reference=None, **data):
        """Atualiza a transacao quando o cliente volta para o Odoo.

        A rota e publica e nao tem assinatura: o que chega nela nao prova nada.
        Por isso os dados recebidos sao ignorados e o status e reconsultado no
        PinBank pelo nosso numero do boleto, como faz o cron.

        :param str reference: The transaction reference embedded in the return URL.
        :param dict data: The data received, ignored on purpose.
        """
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("reference", "=", reference or ""),
                    ("provider_code", "=", "boleto_pinbank"),
                    ("our_number", "!=", False),
                ],
                limit=1,
            )
        )
        if tx_sudo and tx_sudo.state in ("draft", "pending", "authorized"):
            try:
                tx_sudo._send_capture_request()
            except ValidationError:
                _logger.warning(
                    "PinBank: could not check the status of transaction %s",
                    tx_sudo.reference,
                    exc_info=True,
                )
        return request.redirect("/payment/status")
