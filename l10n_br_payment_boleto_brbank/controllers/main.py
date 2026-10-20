# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hmac
import logging

from brbank.erros import ErroBrbank

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import content_disposition, request

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
        """Receive a bank notification (O7): validate, store and answer.

        - An unknown provider and a wrong token get the same empty 404, so
          the route says nothing about which providers exist.
        - The token is compared in constant time.
        - The body becomes canonical events (masked by the library) and is
          stored deduplicated; the processing, which reads the title back
          from the bank, runs in a cron triggered at once.
        """
        provider = request.env["payment.provider"].sudo().browse(provider_id).exists()
        expected = ""
        if provider and provider.code == BRBANK and provider.state != "disabled":
            expected = provider.brbank_webhook_token or ""
        if not (expected and hmac.compare_digest(expected.encode(), token.encode())):
            return request.make_response("", status=404)

        body = request.httprequest.get_data()
        headers = dict(request.httprequest.headers)
        try:
            events = provider._brbank_parse_webhook(body, headers)
        except (ErroBrbank, UserError, ValueError) as error:
            # Never the body: it may carry personal data.
            _logger.info(
                "brbank webhook: provider %s refused a payload (%s)",
                provider.id,
                type(error).__name__,
            )
            return request.make_response("", status=400)
        created = (
            request.env["l10n_br.brbank.event"].sudo()._brbank_store(provider, events)
        )
        if created:
            request.env.ref(
                "l10n_br_payment_boleto_brbank.ir_cron_brbank_process_events"
            ).sudo()._trigger()
        return request.make_json_response(
            {"received": len(events), "new": len(created)}
        )


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
