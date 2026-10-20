# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The refresh token renewed by the bank (BTG) is persisted at once.

The adapter of the library renews the access token with the stored refresh
token and calls `ao_renovar_refresh_token` when the bank returns a new one.
The bank is simulated by an `httpx.MockTransport`: no test reaches a bank.
"""

import json
from urllib.parse import parse_qs

import httpx
from brbank.erros import ErroBrbank

from odoo.tests import HttpCase, tagged

from ..models.payment_provider import RENEWED_TOKENS
from .common import BrbankCommon, BrbankTransactionCase

LOGGER = "odoo.addons.l10n_br_payment_boleto_brbank.models.payment_provider"
BTG_SETTINGS = {
    "cnpj_empresa": "11222333000181",
    "agencia": "1234",
    "conta_corrente": "1234567",
}


class BtgBankMixin:
    """A BTG provider and a fake BTG that rotates the refresh token."""

    def _setup_btg(self):
        self.sent_tokens = []
        self.next_tokens = ["rt-new", "rt-newer"]
        self.collection_status = 200

        def handler(request):
            if request.url.path.endswith("/oauth2/token"):
                form = parse_qs(request.content.decode())
                self.assertEqual(form["grant_type"], ["refresh_token"])
                self.sent_tokens.append(form["refresh_token"][0])
                return httpx.Response(
                    200,
                    json={
                        "access_token": "access-token",
                        "expires_in": 3600,
                        "refresh_token": self.next_tokens.pop(0),
                    },
                )
            if self.collection_status != 200:
                return httpx.Response(
                    self.collection_status, json={"Message": "refused"}
                )
            return httpx.Response(
                200,
                content=b"%PDF-1.4 btg",
                headers={"Content-Type": "application/pdf"},
            )

        self.transport = httpx.MockTransport(handler)

    def _btg_provider(self, provider=None):
        values = {
            "brbank_refresh_token": "rt-old",
            "brbank_extra_config": json.dumps(BTG_SETTINGS),
        }
        if provider:
            values.update(
                brbank_client_id="client-id",
                brbank_client_secret="client-secret",
                state="test",
            )
            provider.write(values)
            return provider
        return self._create_provider("btg", **values)

    def _btg_pdf(self, provider):
        return provider.with_context(brbank_http_transport=self.transport)._brbank_run(
            lambda adapter: adapter.obter_pdf("collection-1")
        )


@tagged("post_install", "-at_install")
class TestRefreshTokenCommitted(BtgBankMixin, BrbankCommon, HttpCase):
    """Own cursor path: `HttpCase` runs in test mode, so the cursor opened by
    the callback is a test cursor on the same connection and the commit
    lands where the test can read it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_brbank()

    def setUp(self):
        super().setUp()
        self._setup_btg()

    def _stored_token(self, provider):
        with self.registry.cursor() as cr:
            cr.execute(
                "SELECT brbank_refresh_token FROM payment_provider WHERE id = %s",
                (provider.id,),
            )
            return cr.fetchone()[0]

    def test_renewed_token_committed_and_reused(self):
        provider = self._btg_provider()
        self.assertEqual(self._btg_pdf(provider), b"%PDF-1.4 btg")
        self.assertEqual(self.sent_tokens, ["rt-old"])
        self.assertEqual(self._stored_token(provider), "rt-new")
        # The next call of the same transaction renews with the new token,
        # not with the one of the transaction snapshot.
        self.assertEqual(self.env.cr.cache[RENEWED_TOKENS][provider.id], "rt-new")
        self._btg_pdf(provider)
        self.assertEqual(self.sent_tokens, ["rt-old", "rt-new"])
        self.assertEqual(self._stored_token(provider), "rt-newer")
        _adapter_class, config = provider._brbank_prepare_adapter()
        self.assertEqual(config.refresh_token, "rt-newer")
        self.assertNotIn("rt-newer", repr(config))

    def test_renewed_token_survives_a_failed_call(self):
        """The bank refuses the operation after renewing the token."""
        provider = self._btg_provider()
        self.collection_status = 400
        # Not `assertRaises`: the Odoo one rolls back a savepoint, and in test
        # mode the cursor of the callback shares the connection of the test.
        try:
            self._btg_pdf(provider)
        except ErroBrbank:
            refused = True
        else:
            refused = False
        self.assertTrue(refused)
        self.assertEqual(self.sent_tokens, ["rt-old"])
        self.assertEqual(self._stored_token(provider), "rt-new")


@tagged("post_install", "-at_install")
class TestRefreshTokenFallback(BtgBankMixin, BrbankTransactionCase):
    """Without test mode the callback opens a real cursor: it cannot see a
    provider of the test transaction, nor lock a row this transaction wrote,
    so the token goes to the current transaction (with a warning)."""

    def setUp(self):
        super().setUp()
        self._setup_btg()

    def _assert_fallback(self, provider, reason):
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            self._btg_pdf(provider)
        output = "\n".join(logs.output)
        self.assertIn("current transaction only", output)
        self.assertIn(reason, output)
        self.assertNotIn("rt-new", output)
        self.assertEqual(self.sent_tokens, ["rt-old"])
        self.assertEqual(provider.brbank_refresh_token, "rt-new")
        self.assertNotIn(provider.id, self.env.cr.cache.get(RENEWED_TOKENS, {}))

    def test_provider_not_committed(self):
        self._assert_fallback(self._btg_provider(), "not committed yet")

    def test_row_locked_by_the_caller(self):
        """No deadlock: the provider row is locked by this transaction, which
        waits for the bank call; the callback gives up at once (NOWAIT)."""
        provider = self.env.ref(
            "l10n_br_payment_boleto_brbank.payment_provider_brbank_btg"
        )
        self._assert_fallback(self._btg_provider(provider), "LockNotAvailable")
