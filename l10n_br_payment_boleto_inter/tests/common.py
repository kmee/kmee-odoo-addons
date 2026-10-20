# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import TransactionCase

PDF_CONTENT = b"%PDF-1.4 fake boleto"


class ResponseStub:
    """Resposta mínima de requests, para não tocar a rede nos testes."""

    def __init__(self, status_code=200, content=None, json_data=None):
        self.status_code = status_code
        self._json = json_data
        if content is None and json_data is not None:
            content = json.dumps(json_data).encode()
        self.content = content or b""
        self.text = self.content.decode(errors="replace")

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class SessionStub:
    """Sessão que devolve respostas programadas e registra as chamadas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.cert = None
        self.verify = None
        self.closed = False

    def _next(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        return self._next("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._next("GET", url, **kwargs)

    def close(self):
        self.closed = True


class BancoInterCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.provider = cls.env["payment.provider"].create(
            {
                "name": "Banco Inter (TEST)",
                "code": "inter",
                "state": "test",
                "inter_conta_corrente": "123456",
                "inter_client_id": "dummy-client-id",
                "inter_client_secret": "dummy-client-secret",
                "inter_certificate": base64.b64encode(b"certificate"),
                "inter_private_key": base64.b64encode(b"private-key"),
            }
        )
        cls.mixin = cls.env["payment.transaction"]

        cls.codigo_solicitacao = "5f9d2e7a-4a29-4b4f-8a4a-2f0d7a0f1c3b"
        cls.token_response = ResponseStub(
            json_data={"access_token": "tok-123", "expires_in": 3600}
        )

    @contextmanager
    def _patch_session(self, responses):
        """Substitui a sessão do mixin por uma que responde do roteiro."""
        session = SessionStub(responses)

        @contextmanager
        def _fake_session(_self, provider_id):
            yield session

        with patch(
            "odoo.addons.l10n_br_payment_boleto_inter.models.banco_inter_mixin"
            ".BancoInterMixin._inter_session",
            _fake_session,
        ):
            yield session

    def _clear_token_cache(self):
        params = self.env["ir.config_parameter"].sudo()
        for param in params.search([("key", "like", "bancointer.token")]):
            param.unlink()
