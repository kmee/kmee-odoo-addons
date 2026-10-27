# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import content_disposition, request

from odoo.addons.l10n_br_bank_connection.controllers.main import (
    dispatch_webhook,
    token_matches,
)
from odoo.addons.portal.controllers.portal import CustomerPortal

from ..models.payment_provider import BRBANK, WEBHOOK_ROUTE

_logger = logging.getLogger(__name__)


class BrbankWebhookController(http.Controller):
    @http.route(
        WEBHOOK_ROUTE + "/<int:provider_id>/<string:token>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def brbank_webhook(self, provider_id, token, **kwargs):
        """Alias of the webhook of the connection (O7), for the URLs that were
        registered at the banks before the connection took it over.

        The provider leads to its connection, and the connection does the
        rest (see `l10n_br_bank_connection`): an unknown provider, a disabled
        one and a wrong token get the same empty 404, the token is compared
        in constant time, the events are stored and processed by a cron.
        """
        provider = request.env["payment.provider"].sudo().browse(provider_id).exists()
        connection = (
            provider.brbank_connection_id
            if provider and provider.code == BRBANK and provider.state != "disabled"
            else provider.brbank_connection_id.browse()
        )
        expected = connection.webhook_token if connection.active else ""
        if not token_matches(expected, token):
            return request.make_response("", status=404)
        return dispatch_webhook(connection)


class BrbankPortal(CustomerPortal):
    @http.route(
        "/my/invoices/<int:invoice_id>/brbank/<int:transaction_id>",
        type="http",
        auth="public",
    )
    def portal_brbank_boleto(
        self, invoice_id, transaction_id, access_token=None, download=False, **kw
    ):
        """PDF of a boleto of the invoice, with the access token of the
        invoice (O5)."""
        try:
            invoice_sudo = self._document_check_access(
                "account.move", invoice_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        transaction = invoice_sudo._brbank_report_transactions().filtered(
            lambda t: t.id == transaction_id and t.boleto_pdf
        )
        if not transaction:
            raise request.not_found()
        filename = f"boleto-{transaction.id}.pdf"
        disposition = (
            content_disposition(filename)
            if download
            else 'inline; filename="%s"' % filename
        )
        return request.make_response(
            base64.b64decode(transaction.boleto_pdf),
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", disposition),
            ],
        )
