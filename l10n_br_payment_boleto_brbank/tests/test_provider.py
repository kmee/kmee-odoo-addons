# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from unittest.mock import patch

import httpx
from brbank import registro

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from ..utils import config as brbank_config
from .common import FAKE, BrbankTransactionCase

# The 13 providers delivered as data: one per bank adapter and Pix profile.
DATA_PROVIDERS = {
    "payment_provider_brbank_inter": "inter",
    "payment_provider_brbank_pinbank": "pinbank",
    "payment_provider_brbank_sicoob": "sicoob",
    "payment_provider_brbank_sicredi": "sicredi",
    "payment_provider_brbank_bb": "bb",
    "payment_provider_brbank_pix_inter": "pix_inter",
    "payment_provider_brbank_pix_bb": "pix_bb",
    "payment_provider_brbank_pix_sicoob": "pix_sicoob",
    "payment_provider_brbank_pix_sicredi": "pix_sicredi",
    "payment_provider_brbank_pix_itau": "pix_itau",
    "payment_provider_brbank_pix_bradesco": "pix_bradesco",
    "payment_provider_brbank_pix_santander": "pix_santander",
    "payment_provider_brbank_pix_efi": "pix_efi",
}
SECRET_FIELDS = (
    "brbank_client_id",
    "brbank_client_secret",
    "brbank_username",
    "brbank_password",
    "brbank_certificate",
    "brbank_private_key",
    "brbank_pix_key",
    "brbank_extra_config",
    "brbank_secret_config",
    "brbank_webhook_token",
    "brbank_webhook_url",
)
DUMMY_BY_TYPE = {bool: False, int: 1, float: 1.0, str: "1234567", bytes: b"x"}


def _no_network(request):
    raise AssertionError(f"unexpected HTTP call to {request.url.host}")


@tagged("post_install", "-at_install")
class TestBrbankProvider(BrbankTransactionCase):
    def test_every_adapter_is_selectable(self):
        """O1: the selection comes from the entry points of the library."""
        adapters = dict(self.env["payment.provider"]._selection_brbank_adapter())
        for name in ("inter", "pinbank", "sicoob", "sicredi", "bb", "pix_bacen"):
            self.assertIn(name, adapters)
        self.assertIn(FAKE, adapters)
        profiles = dict(self.env["payment.provider"]._selection_brbank_pix_perfil())
        self.assertEqual(
            set(profiles),
            {
                "inter",
                "bb",
                "sicoob",
                "sicredi",
                "itau",
                "bradesco",
                "santander",
                "efi",
            },
        )

    def _fill_for_test(self, provider):
        """Dummy credentials and settings typed after the adapter config."""
        provider.action_brbank_fill_settings_template()
        config_cls = brbank_config.config_class(
            registro.obter_classe(provider.brbank_adapter)
        )
        public = json.loads(provider.brbank_extra_config)
        secret = json.loads(provider.brbank_secret_config)
        for key in brbank_config.describe(config_cls):
            target = secret if key["secret"] else public
            if key["required"] and not key["generic"]:
                target[key["name"]] = DUMMY_BY_TYPE.get(key["type"], "1234567")
        provider.write(
            {
                "brbank_client_id": "client-id",
                "brbank_client_secret": "client-secret",
                "brbank_username": "usuario",
                # The PinBank password is also its AES key: 16 bytes.
                "brbank_password": "0123456789abcdef",
                "brbank_pix_key": "pix@example.com",
                "brbank_extra_config": json.dumps(public),
                "brbank_secret_config": json.dumps(secret),
                "state": "enabled",
            }
        )

    def test_every_data_provider_builds_its_adapter(self):
        """O1: each of the 13 data providers instantiates its adapter."""
        transport = httpx.MockTransport(_no_network)
        for xmlid, bank in DATA_PROVIDERS.items():
            with self.subTest(provider=xmlid):
                provider = self.env.ref(f"l10n_br_payment_boleto_brbank.{xmlid}")
                self.assertEqual(provider.code, "brbank")
                self.assertEqual(provider.state, "disabled")
                self.assertFalse(provider.is_published)
                self._fill_for_test(provider)
                with patch.object(
                    type(provider), "_brbank_http_transport", lambda self: transport
                ):
                    built = provider._brbank_run(
                        lambda adapter: (adapter.banco, type(adapter).__name__)
                    )
                self.assertEqual(built[0], bank)
                self.assertTrue(provider.brbank_capabilities)

    def test_incomplete_configuration_is_refused(self):
        provider = self.env.ref(
            "l10n_br_payment_boleto_brbank.payment_provider_brbank_bb"
        )
        with self.assertRaisesRegex(ValidationError, "convenio"):
            provider.write(
                {
                    "brbank_client_id": "id",
                    "brbank_client_secret": "secret",
                    "state": "test",
                }
            )

    def test_secret_typed_in_public_settings_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "chave_api"):
            self.provider.brbank_extra_config = json.dumps(
                {"numero_cliente": 1, "chave_api": "segredo"}
            )

    def test_invalid_json_is_refused(self):
        with self.assertRaises(ValidationError):
            self.provider.brbank_extra_config = "{not json"

    def test_out_of_checkout(self):
        """O9: brbank providers are never offered in the online checkout."""
        providers = self.env["payment.provider"]._get_compatible_providers(
            self.env.company.id, self.partner.id, 100.0
        )
        self.assertNotIn(self.provider, providers)

    def test_secrets_hidden_from_non_admin(self):
        """Credentials are readable by system administrators only.

        `payment` already keeps the providers to the settings group; the
        field groups still hide the secrets if another module grants read
        access on the providers to other users (simulated here).
        """
        user = new_test_user(
            self.env,
            login="brbank-billing",
            groups="base.group_user,account.group_account_manager",
        )
        with self.assertRaises(AccessError):
            self.provider.with_user(user).read(["name"])
        self.env["ir.model.access"].create(
            {
                "name": "test: managers read providers",
                "model_id": self.env.ref("payment.model_payment_provider").id,
                "group_id": self.env.ref("account.group_account_manager").id,
                "perm_read": True,
            }
        )
        provider = self.provider.with_user(user)
        self.assertEqual(provider.read(["name"])[0]["name"], self.provider.name)
        fields_seen = provider.fields_get()
        for field_name in SECRET_FIELDS:
            self.assertNotIn(field_name, fields_seen)
            with self.assertRaises(AccessError):
                provider.read([field_name])
        arch = (
            self.env["payment.provider"]
            .with_user(user)
            .get_view(view_type="form")["arch"]
        )
        for field_name in SECRET_FIELDS:
            self.assertNotIn(f'name="{field_name}"', arch)
        # The capabilities, needed by the views, stay readable.
        self.assertTrue(provider.brbank_capabilities)

    def test_webhook_token_rotation(self):
        old_url = self.provider.brbank_webhook_url
        self.assertIn(f"/payment/brbank/webhook/{self.provider.id}/", old_url)
        self.provider.action_brbank_rotate_webhook_token()
        self.assertNotEqual(self.provider.brbank_webhook_url, old_url)

    def test_certificate_reaches_the_config_decoded(self):
        """The PEM goes to the library as bytes, only in memory."""
        provider = self.env.ref(
            "l10n_br_payment_boleto_brbank.payment_provider_brbank_inter"
        )
        provider.write(
            {
                "brbank_client_id": "id",
                "brbank_client_secret": "secret",
                "brbank_certificate": base64.b64encode(b"-----BEGIN CERTIFICATE-----"),
                "brbank_private_key": base64.b64encode(b"-----BEGIN PRIVATE KEY-----"),
            }
        )
        self.assertTrue(provider.brbank_uses_certificate)
        _adapter_class, config = provider._brbank_prepare_adapter()
        self.assertEqual(config.certificado_pem, b"-----BEGIN CERTIFICATE-----")
        self.assertEqual(config.chave_pem, b"-----BEGIN PRIVATE KEY-----")
        self.assertEqual(config.conta, f"odoo-provider-{provider.id}")

    def test_config_built_from_the_provider(self):
        self.provider.brbank_extra_config = json.dumps({"numero_cliente": 7})
        _adapter_class, config = self.provider._brbank_prepare_adapter()
        self.assertEqual(config.numero_cliente, 7)
        self.assertEqual(config.ambiente, "sandbox")
        self.assertNotIn("client-secret", repr(config))
