# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

import httpx
from brbank import registro

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged

from ..models.payment_provider import NOSSO_NUMERO_DIGITS
from .common import FAKE, BrbankTransactionCase

# The 22 providers delivered as data: one per bank adapter and Pix profile.
DATA_PROVIDERS = {
    "payment_provider_brbank_inter": "inter",
    "payment_provider_brbank_pinbank": "pinbank",
    "payment_provider_brbank_sicoob": "sicoob",
    "payment_provider_brbank_sicredi": "sicredi",
    "payment_provider_brbank_bb": "bb",
    "payment_provider_brbank_itau": "itau",
    "payment_provider_brbank_bradesco": "bradesco",
    "payment_provider_brbank_santander": "santander",
    "payment_provider_brbank_btg": "btg",
    "payment_provider_brbank_c6": "c6",
    "payment_provider_brbank_banrisul": "banrisul",
    "payment_provider_brbank_unicred": "unicred",
    "payment_provider_brbank_caixa": "caixa",
    "payment_provider_brbank_safra": "safra",
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
    "client_id",
    "client_secret",
    "username",
    "password",
    "certificate",
    "private_key",
    "pix_key",
    "refresh_token",
    "extra_config",
    "secret_config",
    "scopes",
    "webhook_token",
    "webhook_url",
)
CALLABLE_KEYS = ("gerar_nosso_numero", "ao_renovar_refresh_token")


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

    def test_every_data_provider_builds_its_adapter(self):
        """O1: each of the 22 data providers instantiates its adapter."""
        self.assertEqual(len(DATA_PROVIDERS), 22)
        transport = httpx.MockTransport(_no_network)
        for xmlid, bank in DATA_PROVIDERS.items():
            with self.subTest(provider=xmlid):
                provider = self.env.ref(f"l10n_br_payment_brbank.{xmlid}")
                self.assertEqual(provider.code, "brbank")
                self.assertEqual(provider.state, "disabled")
                self.assertFalse(provider.is_published)
                connection = self._fill_for_test(provider)
                # Callable keys never go to the JSON settings.
                settings = json.loads(connection.extra_config)
                settings.update(json.loads(connection.secret_config))
                for name in CALLABLE_KEYS:
                    self.assertNotIn(name, settings)
                built = provider.with_context(
                    brbank_http_transport=transport
                )._brbank_run(lambda adapter: (adapter.banco, type(adapter).__name__))
                self.assertEqual(built[0], bank)
                adapter_class = registro.obter_classe(provider.brbank_adapter)
                self.assertEqual(
                    bool(provider.brbank_capabilities), bool(adapter_class.capacidades)
                )
                _adapter_class, config = provider._brbank_prepare_adapter()
                # The nosso numero comes from the sequence of the provider.
                if hasattr(config, "gerar_nosso_numero"):
                    self.assertIn(bank, NOSSO_NUMERO_DIGITS)
                    self.assertTrue(callable(config.gerar_nosso_numero))
                if hasattr(config, "ao_renovar_refresh_token"):
                    self.assertTrue(callable(config.ao_renovar_refresh_token))
                    self.assertEqual(config.refresh_token, "refresh-token")
                    self.assertTrue(connection.uses_refresh_token)
                else:
                    self.assertFalse(connection.uses_refresh_token)

    def test_adapter_without_test_environment_refuses_test_environment(self):
        """Caixa has no sandbox: the test environment would reach production."""
        provider = self.env.ref("l10n_br_payment_brbank.payment_provider_brbank_caixa")
        connection = self._fill_for_test(provider)
        self.assertEqual(provider.state, "enabled")
        with self.assertRaisesRegex(ValidationError, "no test environment"):
            connection.environment = "test"

    def test_incomplete_configuration_is_refused(self):
        """A draft connection may be incomplete; a connected one may not."""
        connection = self._create_connection(
            "bb", state="draft", extra_config=False, client_id="id"
        )
        with self.assertRaisesRegex(ValidationError, "convenio"):
            connection.state = "connected"
        provider = self.env.ref("l10n_br_payment_brbank.payment_provider_brbank_bb")
        provider.brbank_connection_id = connection
        with self.assertRaisesRegex(ValidationError, "convenio"):
            provider.state = "test"

    def test_enabled_provider_needs_a_connection_of_its_adapter(self):
        provider = self.env.ref("l10n_br_payment_brbank.payment_provider_brbank_bb")
        with self.assertRaisesRegex(ValidationError, "bank connection"):
            provider.state = "test"
        with self.assertRaisesRegex(ValidationError, "another bank adapter"):
            provider.write(
                {"brbank_connection_id": self.provider.brbank_connection_id.id}
            )
            provider.state = "test"

    def test_onchange_connection_sets_the_adapter(self):
        provider = self.env["payment.provider"].new(
            {
                "code": "brbank",
                "brbank_connection_id": self.provider.brbank_connection_id,
            }
        )
        provider._onchange_brbank_connection_id()
        self.assertEqual(provider.brbank_adapter, FAKE)

    def test_provider_without_connection_cannot_call_the_bank(self):
        provider = self.env.ref("l10n_br_payment_brbank.payment_provider_brbank_bb")
        with self.assertRaisesRegex(UserError, "no bank connection"):
            provider._brbank_connection()

    def test_secret_typed_in_public_settings_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "chave_api"):
            self.provider.brbank_connection_id.extra_config = json.dumps(
                {"numero_cliente": 1, "chave_api": "segredo"}
            )

    def test_invalid_json_is_refused(self):
        with self.assertRaises(ValidationError):
            self.provider.brbank_connection_id.extra_config = "{not json"

    def test_out_of_checkout(self):
        """O9: brbank providers are never offered in the online checkout."""
        providers = self.env["payment.provider"]._get_compatible_providers(
            self.env.company.id, self.partner.id, 100.0
        )
        self.assertNotIn(self.provider, providers)

    def test_provider_secrets_are_not_on_the_provider_anymore(self):
        """The credentials moved to the connection (see its own tests)."""
        fields_seen = self.env["payment.provider"].fields_get()
        for field_name in ("brbank_client_id", "brbank_refresh_token"):
            self.assertNotIn(field_name, fields_seen)
        self.assertIn("brbank_connection_id", fields_seen)

    def test_secrets_hidden_from_non_admin(self):
        """Credentials are readable by system administrators only.

        The record rules and the ACL keep the connections to the bank
        connection administrators and, read only, to the account managers;
        the field groups still hide the secrets from them.
        """
        connection = self.provider.brbank_connection_id
        manager = new_test_user(
            self.env,
            login="brbank-billing",
            groups="base.group_user,account.group_account_manager",
        )
        connection_manager = connection.with_user(manager)
        self.assertEqual(connection_manager.read(["name"])[0]["name"], connection.name)
        with self.assertRaises(AccessError):
            connection_manager.write({"name": "other"})
        fields_seen = connection_manager.fields_get()
        for field_name in SECRET_FIELDS:
            self.assertNotIn(field_name, fields_seen)
            with self.assertRaises(AccessError):
                connection_manager.read([field_name])
        arch = (
            self.env["l10n_br_bank_connection.connection"]
            .with_user(manager)
            .get_view(view_type="form")["arch"]
        )
        for field_name in SECRET_FIELDS:
            self.assertNotIn(f'name="{field_name}"', arch)
        # What the views need stays readable.
        self.assertEqual(connection_manager.adapter, FAKE)
        self.assertTrue(self.provider.brbank_capabilities)

    def test_certificate_reaches_the_config_decoded(self):
        """The PEM goes to the library as bytes, only in memory."""
        provider = self.env.ref("l10n_br_payment_brbank.payment_provider_brbank_inter")
        connection = self._create_connection(
            "inter",
            extra_config=False,
            certificate=base64.b64encode(b"-----BEGIN CERTIFICATE-----"),
            private_key=base64.b64encode(b"-----BEGIN PRIVATE KEY-----"),
        )
        provider.brbank_connection_id = connection
        self.assertTrue(connection.uses_certificate)
        _adapter_class, config = provider._brbank_prepare_adapter()
        self.assertEqual(config.certificado_pem, b"-----BEGIN CERTIFICATE-----")
        self.assertEqual(config.chave_pem, b"-----BEGIN PRIVATE KEY-----")
        self.assertEqual(config.conta, f"odoo-connection-{connection.id}")

    def test_config_built_from_the_connection(self):
        connection = self.provider.brbank_connection_id
        connection.extra_config = json.dumps({"numero_cliente": 7})
        _adapter_class, config = self.provider._brbank_prepare_adapter()
        self.assertEqual(config.numero_cliente, 7)
        self.assertEqual(config.ambiente, "sandbox")
        self.assertNotIn("client-secret", repr(config))
        connection.environment = "prod"
        _adapter_class, config = self.provider._brbank_prepare_adapter()
        self.assertEqual(config.ambiente, "producao")
