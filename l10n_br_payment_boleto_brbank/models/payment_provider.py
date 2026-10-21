# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import inspect
import json
import logging
import secrets

import httpx
import psycopg2
from brbank import Capacidade, registro
from brbank.erros import AdapterNaoEncontrado, ErroBrbank, Validacao

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils import config as brbank_config
from ..utils.runner import run_in_dedicated_loop

_logger = logging.getLogger(__name__)

BRBANK = "brbank"
WEBHOOK_ROUTE = "/payment/brbank/webhook"

ADAPTER_LABELS = {
    "banrisul": "Banrisul (041)",
    "bb": "Banco do Brasil (001)",
    "bradesco": "Bradesco (237)",
    "btg": "BTG Pactual (208)",
    "c6": "C6 Bank (336)",
    "caixa": "Caixa (104)",
    "inter": "Banco Inter (077)",
    "itau": "Itaú (341)",
    "pinbank": "PinBank",
    "pix_bacen": "Pix (BACEN API)",
    "safra": "Safra (422)",
    "santander": "Santander (033)",
    "sicoob": "Sicoob (756)",
    "sicredi": "Sicredi (748)",
    "unicred": "Unicred (136)",
}
PIX_PROFILE_LABELS = {
    "bb": "Banco do Brasil",
    "bradesco": "Bradesco",
    "efi": "Efí",
    "inter": "Banco Inter",
    "itau": "Itaú",
    "santander": "Santander",
    "sicoob": "Sicoob",
    "sicredi": "Sicredi",
}
# Generic provider field -> key used by the adapter configurations.
GENERIC_FIELDS = {
    "brbank_client_id": "client_id",
    "brbank_client_secret": "client_secret",
    "brbank_username": "usuario",
    "brbank_password": "senha",
    "brbank_certificate": "certificado_pem",
    "brbank_private_key": "chave_pem",
    "brbank_pix_key": "chave_pix",
    "brbank_refresh_token": "refresh_token",
}
# Callable keys of the adapter configurations served by the provider, with
# the method that builds the function. The other callable keys (such as
# `gerar_nosso_numero`) keep the library default.
CALLBACK_FACTORIES = {
    "ao_renovar_refresh_token": "_brbank_refresh_token_callback",
    "gerar_nosso_numero": "_brbank_nosso_numero_callback",
}
# Largest nosso numero (digits) the `gerar_nosso_numero` of each adapter
# accepts, as validated by the library (Banrisul: the 8 free digits, the
# adapter adds the check digits; Caixa: without the "14" prefix). An adapter
# that takes the generator but is missing here keeps the library default.
NOSSO_NUMERO_DIGITS = {
    "banrisul": 8,
    "bb": 10,
    "caixa": 15,
    "itau": 8,
    "safra": 9,
    "santander": 12,
}
# Context key with the nosso numero reserved for each title, by idempotency
# key, read by the `gerar_nosso_numero` given to the adapter.
NOSSO_NUMERO_CONTEXT = "brbank_nosso_numeros"
# Key of `cr.cache` with the refresh tokens renewed in the current transaction.
RENEWED_TOKENS = "brbank_renewed_refresh_tokens"
SECRET_GROUP = "base.group_system"


def _save_refresh_token(registry, provider_id, token):
    """Commit a renewed refresh token in a transaction of its own.

    The bank already invalidated the old token, so the new one must survive a
    rollback of the transaction that called the bank. Runs in the thread of
    the bank call, so it never touches the environment of the caller: only
    the registry and the provider id. `NOWAIT` turns a row locked by another
    transaction (possibly the caller, which waits for this thread) into an
    immediate failure instead of a deadlock.

    :return: None when the token was committed, else why it was not.
    :rtype: str
    """
    try:
        with registry.cursor() as cr:
            cr.execute(
                "SELECT id FROM payment_provider WHERE id = %s FOR UPDATE NOWAIT",
                (provider_id,),
                log_exceptions=False,
            )
            if not cr.fetchone():
                # Provider created in the caller transaction, not committed.
                return "provider not committed yet"
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["payment.provider"].browse(provider_id).write(
                {"brbank_refresh_token": token}
            )
        return None
    except psycopg2.Error as error:
        return type(error).__name__


def _capability_labels():
    return {
        Capacidade.HIBRIDO: _("Hybrid boleto (Pix QR code)"),
        Capacidade.SO_HIBRIDO: _("Hybrid boleto only"),
        Capacidade.ALTERACAO: _("Instructions (due date, rebate)"),
        Capacidade.BAIXA: _("Write-off"),
        Capacidade.PDF: _("Boleto PDF"),
        Capacidade.WEBHOOK: _("Webhook"),
        Capacidade.PIX_COB: _("Immediate Pix charge"),
        Capacidade.PIX_COBV: _("Pix charge with due date"),
        Capacidade.EMISSAO_ASSINCRONA: _("Asynchronous registration"),
        Capacidade.INSTRUCAO_ASSINCRONA: _("Asynchronous instructions"),
        Capacidade.CNAB_REMESSA: _("CNAB remittance"),
    }


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[(BRBANK, "Brazilian bank (brbank)")],
        ondelete={BRBANK: "set default"},
    )
    brbank_adapter = fields.Selection(
        selection="_selection_brbank_adapter",
        string="Bank Adapter",
        help="Adapter of the brbank library that talks to the bank.",
    )
    brbank_pix_perfil = fields.Selection(
        selection="_selection_brbank_pix_perfil",
        string="Pix Profile",
        help="Bank (PSP) of the Pix BACEN adapter.",
    )

    # Credentials: readable by system administrators only.
    brbank_client_id = fields.Char(string="Bank Client ID", groups=SECRET_GROUP)
    brbank_client_secret = fields.Char(string="Bank Client Secret", groups=SECRET_GROUP)
    brbank_username = fields.Char(string="API Username", groups=SECRET_GROUP)
    brbank_password = fields.Char(string="API Password", groups=SECRET_GROUP)
    brbank_certificate = fields.Binary(
        string="Certificate (PEM)",
        attachment=False,
        groups=SECRET_GROUP,
        help="mTLS certificate. It only goes to a temporary file in memory "
        "while the TLS context is built.",
    )
    brbank_private_key = fields.Binary(
        string="Private Key (PEM)", attachment=False, groups=SECRET_GROUP
    )
    brbank_pix_key = fields.Char(string="Pix Key", groups=SECRET_GROUP)
    brbank_refresh_token = fields.Char(
        string="Refresh Token",
        groups=SECRET_GROUP,
        copy=False,
        help="OAuth refresh token obtained once at the bank (authorization "
        "code flow). The bank may return a new one at each renewal: the "
        "provider keeps it up to date by itself.",
    )
    brbank_extra_config = fields.Text(
        string="Extra Settings",
        groups=SECRET_GROUP,
        help="JSON object with the bank specific settings (agreement, wallet, "
        "client number...). Use 'Fill settings template' to get the keys.",
    )
    brbank_secret_config = fields.Text(
        string="Extra Secrets",
        groups=SECRET_GROUP,
        help="JSON object with the bank specific secrets (developer key, API "
        "key...).",
    )
    brbank_nosso_numero_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Nosso Numero Sequence",
        readonly=True,
        copy=False,
        help="Created at the first title of a bank whose nosso numero is "
        "chosen by the issuer. Numbers are never reused.",
    )
    brbank_webhook_token = fields.Char(
        string="Webhook Token",
        groups=SECRET_GROUP,
        copy=False,
        default=lambda self: secrets.token_urlsafe(32),
    )
    brbank_webhook_url = fields.Char(
        string="Webhook URL", compute="_compute_brbank_webhook_url", groups=SECRET_GROUP
    )

    # What the adapter declares, for the views (O11).
    brbank_capabilities = fields.Char(
        string="Bank Capabilities", compute="_compute_brbank_adapter_info"
    )
    brbank_supports_pdf = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_supports_webhook = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_supports_instruction = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_supports_write_off = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_sandbox_validated = fields.Boolean(
        string="Validated in Sandbox", compute="_compute_brbank_adapter_info"
    )
    brbank_uses_client_id = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_client_secret = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_username = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_password = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_certificate = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_pix_key = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_uses_refresh_token = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_is_pix = fields.Boolean(compute="_compute_brbank_adapter_info")
    brbank_settings_help = fields.Text(
        string="Settings Keys", compute="_compute_brbank_adapter_info"
    )

    # === SELECTIONS === #

    @api.model
    def _selection_brbank_adapter(self):
        """Adapters installed in the brbank library (entry points)."""
        return [
            (name, ADAPTER_LABELS.get(name, name))
            for name in registro.listar_adapters()
        ]

    @api.model
    def _selection_brbank_pix_perfil(self):
        try:
            from brbank.adapters.pix_bacen import PERFIS
        except ImportError:  # pragma: no cover
            return []
        return [(name, PIX_PROFILE_LABELS.get(name, name)) for name in sorted(PERFIS)]

    # === COMPUTE METHODS === #

    def _brbank_adapter_class(self):
        self.ensure_one()
        if self.code != BRBANK or not self.brbank_adapter:
            return None
        try:
            return registro.obter_classe(self.brbank_adapter)
        except AdapterNaoEncontrado:
            return None

    @api.depends("code", "brbank_adapter", "brbank_pix_perfil")
    def _compute_brbank_adapter_info(self):
        labels = _capability_labels()
        for provider in self:
            adapter_class = provider._brbank_adapter_class()
            capabilities = (
                adapter_class.capacidades if adapter_class else Capacidade.NENHUMA
            )
            keys = {}
            if adapter_class:
                try:
                    config_cls = brbank_config.config_class(adapter_class)
                    keys = {k["name"]: k for k in brbank_config.describe(config_cls)}
                except brbank_config.ConfigError:
                    keys = {}
            provider.brbank_capabilities = ", ".join(
                label for flag, label in labels.items() if flag in capabilities
            )
            provider.brbank_supports_pdf = Capacidade.PDF in capabilities
            provider.brbank_supports_webhook = Capacidade.WEBHOOK in capabilities
            provider.brbank_supports_instruction = Capacidade.ALTERACAO in capabilities
            provider.brbank_supports_write_off = Capacidade.BAIXA in capabilities
            provider.brbank_sandbox_validated = provider._brbank_validated(
                adapter_class
            )
            provider.brbank_uses_client_id = "client_id" in keys
            provider.brbank_uses_client_secret = "client_secret" in keys
            provider.brbank_uses_username = "usuario" in keys
            provider.brbank_uses_password = "senha" in keys
            provider.brbank_uses_certificate = "certificado_pem" in keys
            provider.brbank_uses_pix_key = "chave_pix" in keys
            provider.brbank_uses_refresh_token = "refresh_token" in keys
            provider.brbank_is_pix = "perfil" in keys
            provider.brbank_settings_help = "\n".join(
                "{name}: {kind}{required}{secret}".format(
                    name=key["name"],
                    kind=getattr(key["type"], "__name__", "json"),
                    required=_(" (required)") if key["required"] else "",
                    secret=_(" [secret]") if key["secret"] else "",
                )
                for key in keys.values()
                if not key["generic"] and not key["callable"]
            )

    def _brbank_validated(self, adapter_class):
        """Whether the library declares the adapter validated in a sandbox."""
        self.ensure_one()
        if adapter_class is None:
            return False
        if self.brbank_pix_perfil and self.brbank_adapter == "pix_bacen":
            from brbank.adapters.pix_bacen import PERFIS

            profile = PERFIS.get(self.brbank_pix_perfil)
            return bool(profile and profile.validado_sandbox)
        return bool(getattr(adapter_class, "validado_sandbox", False))

    @api.depends("code", "brbank_webhook_token")
    def _compute_brbank_webhook_url(self):
        for provider in self:
            if provider.code != BRBANK or not provider.id:
                provider.brbank_webhook_url = False
                continue
            provider.brbank_webhook_url = "{}{}/{}/{}".format(
                provider.get_base_url(),
                WEBHOOK_ROUTE,
                provider.id,
                provider.brbank_webhook_token or "",
            )

    def _compute_feature_support_fields(self):
        """Override of `payment`: a registered title is an `authorized`
        transaction, so brbank providers declare manual capture (capture
        queries the bank, void writes the title off)."""
        res = super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == BRBANK).update(
            {"support_manual_capture": True}
        )
        return res

    @api.depends("code")
    def _compute_view_configuration_fields(self):
        """Override of `payment`: brbank providers stay out of the checkout."""
        res = super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == BRBANK).update(
            {
                "show_allow_tokenization": False,
                "show_allow_express_checkout": False,
                "show_payment_icon_ids": False,
                "show_pre_msg": False,
                "show_pending_msg": False,
                "show_auth_msg": False,
                "show_done_msg": False,
                "show_cancel_msg": False,
            }
        )
        return res

    # === CONSTRAINTS === #

    @api.constrains(
        "code",
        "state",
        "brbank_adapter",
        "brbank_pix_perfil",
        "brbank_extra_config",
        "brbank_secret_config",
    )
    def _check_brbank_configuration(self):
        for provider in self.sudo():
            if provider.code != BRBANK:
                continue
            provider._brbank_load_json("brbank_extra_config")
            provider._brbank_load_json("brbank_secret_config")
            if provider.state == "disabled":
                continue
            if not provider.brbank_adapter:
                raise ValidationError(_("Choose the bank adapter of the provider."))
            try:
                provider._brbank_prepare_adapter()
            except UserError as error:
                raise ValidationError(error.args[0]) from error

    def _brbank_load_json(self, field_name):
        """Read a JSON settings field as a dict.

        :raise ValidationError: If the text is not a JSON object. The message
            names the field only, never its content.
        """
        self.ensure_one()
        text = self.sudo()[field_name]
        if not text or not text.strip():
            return {}
        try:
            value = json.loads(text)
        except ValueError:
            value = None
        if not isinstance(value, dict):
            raise ValidationError(
                _(
                    "The field %s must hold a JSON object.",
                    self._fields[field_name].string,
                )
            )
        return value

    # === BUSINESS METHODS: CHECKOUT === #

    @api.model
    def _get_compatible_providers(self, *args, **kwargs):
        """Override of `payment`: brbank providers never show in the checkout.

        They issue boletos and Pix charges from invoices; the online payment
        flow (redirect, tokens) is not implemented for them (O9).
        """
        providers = super()._get_compatible_providers(*args, **kwargs)
        return providers.filtered(lambda p: p.code != BRBANK)

    def _get_supported_currencies(self):
        supported_currencies = super()._get_supported_currencies()
        if self.code == BRBANK:
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name == "BRL"
            )
        return supported_currencies

    # === BUSINESS METHODS: ADAPTER === #

    def _brbank_prepare_adapter(self, callback_outcome=None):
        """Read the provider and build the adapter class and configuration.

        Runs in the calling thread, with sudo: the secrets never leave the
        configuration object handed to the library.

        :param dict callback_outcome: Filled by the callbacks given to the
            adapter (see `_brbank_after_call`).
        :return: The adapter class and its configuration.
        :rtype: tuple
        :raise UserError: If the configuration is incomplete. The message
            names the missing keys, never their values.
        """
        self.ensure_one()
        provider = self.sudo()
        if provider.code != BRBANK or not provider.brbank_adapter:
            raise UserError(_("This provider is not a brbank provider."))
        try:
            adapter_class = registro.obter_classe(provider.brbank_adapter)
        except AdapterNaoEncontrado as error:
            raise UserError(
                _(
                    "The bank adapter %s is not installed in the brbank library.",
                    provider.brbank_adapter,
                )
            ) from error
        generic = {
            "conta": f"odoo-provider-{provider.id}",
            "ambiente": "sandbox" if provider.state == "test" else "producao",
            "perfil": provider.brbank_pix_perfil,
        }
        for field_name, key in GENERIC_FIELDS.items():
            value = provider[field_name]
            if value and provider._fields[field_name].type == "binary":
                value = base64.b64decode(value)
            generic[key] = value
        renewed = self.env.cr.cache.get(RENEWED_TOKENS, {}).get(provider.id)
        if renewed:
            generic["refresh_token"] = renewed
        if callback_outcome is None:
            callback_outcome = {}
        try:
            config_cls = brbank_config.config_class(adapter_class)
            keys = {key["name"] for key in brbank_config.describe(config_cls)}
            if provider.state == "test" and "ambiente" not in keys:
                raise UserError(
                    _(
                        "The bank adapter %s has no test environment: every call "
                        "reaches production. Enable the provider instead of using "
                        "the test mode, and validate it with a low amount.",
                        provider.brbank_adapter,
                    )
                )
            callbacks = {
                key: getattr(provider, method)(callback_outcome)
                for key, method in CALLBACK_FACTORIES.items()
                if key in keys
            }
            config = brbank_config.build(
                config_cls,
                generic,
                provider._brbank_load_json("brbank_extra_config"),
                provider._brbank_load_json("brbank_secret_config"),
                callbacks=callbacks,
            )
        except brbank_config.ConfigError as error:
            parts = []
            if error.missing:
                parts.append(_("missing: %s", ", ".join(error.missing)))
            if error.unknown:
                parts.append(_("unknown or invalid: %s", ", ".join(error.unknown)))
            if error.misplaced:
                parts.append(
                    _(
                        "secrets typed in Extra Settings, move them to Extra "
                        "Secrets: %s",
                        ", ".join(error.misplaced),
                    )
                )
            raise UserError(
                _(
                    "Incomplete configuration of the provider %(name)s (%(details)s).",
                    name=provider.name,
                    details="; ".join(parts),
                )
            ) from error
        except ErroBrbank as error:
            raise UserError(
                _(
                    "The bank refused the configuration of the provider "
                    "%(name)s: %(error)s",
                    name=provider.name,
                    error=error,
                )
            ) from error
        return adapter_class, config

    def _brbank_http_transport(self):
        """HTTP transport given to the adapter; None uses the real network.

        Tests pass an `httpx.MockTransport` in the context key
        `brbank_http_transport` (or override this method): no test ever
        reaches a bank. Anything else in that key is ignored.
        """
        transport = self.env.context.get("brbank_http_transport")
        if isinstance(transport, httpx.AsyncBaseTransport):
            return transport
        return None

    def _brbank_run(self, operation):
        """Call the bank through the adapter of the provider.

        The single bridge between the synchronous Odoo and the asynchronous
        library: the adapter is built, used and closed inside a dedicated
        event loop (see `utils.runner`).

        :param operation: Callable receiving the adapter and returning a
            value or an awaitable (e.g. ``lambda a: a.consultar_titulo(x)``).
        :return: The result of the operation.
        :raise brbank.erros.ErroBrbank: The canonical errors of the library,
            for the caller to handle (`Duplicado`, `Validacao`,
            `Indisponivel`).
        """
        self.ensure_one()
        if self.state == "disabled":
            raise UserError(_("The payment provider %s is disabled.", self.name))
        # Pending writes on the provider become row locks before the call, so
        # a callback committing apart sees them (NOWAIT) instead of racing a
        # later flush of this transaction.
        self.flush_recordset()
        outcome = {}
        adapter_class, config = self._brbank_prepare_adapter(callback_outcome=outcome)
        transport = self._brbank_http_transport()

        async def call():
            kwargs = {}
            if transport is not None:
                kwargs["client"] = httpx.AsyncClient(transport=transport)
            adapter = adapter_class(config, **kwargs)
            try:
                result = operation(adapter)
                if inspect.isawaitable(result):
                    result = await result
                return result
            finally:
                await adapter.aclose()

        try:
            return run_in_dedicated_loop(call)
        finally:
            self._brbank_after_call(outcome)

    # === BUSINESS METHODS: NOSSO NUMERO === #

    def _brbank_nosso_numero_digits(self):
        """Digits of the nosso numero the provider generates, or None.

        None when the adapter does not take `gerar_nosso_numero` (the bank
        numbers the title) or is not in `NOSSO_NUMERO_DIGITS`.
        """
        self.ensure_one()
        adapter_class = self._brbank_adapter_class()
        if not adapter_class or self.brbank_adapter not in NOSSO_NUMERO_DIGITS:
            return None
        try:
            config_cls = brbank_config.config_class(adapter_class)
        except brbank_config.ConfigError:
            return None
        keys = {key["name"] for key in brbank_config.describe(config_cls)}
        if "gerar_nosso_numero" not in keys:
            return None
        return NOSSO_NUMERO_DIGITS[self.brbank_adapter]

    def _brbank_nosso_numero_start(self, digits):
        """First number of a new sequence: after every number this provider
        may already have sent, so none is reused.

        Before the sequence, the adapters used the numeric reference of the
        transaction (`brbank_seu_numero`) as nosso numero: it counts for the
        titles the bank registered with it.
        """
        self.ensure_one()
        txs = (
            self.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("provider_id", "=", self.id),
                    "|",
                    ("brbank_nosso_numero", "!=", False),
                    ("provider_reference", "!=", False),
                ]
            )
        )
        used = [0]
        for tx in txs:
            value = tx.brbank_nosso_numero or tx.brbank_seu_numero
            if value and value.isdigit() and len(value) <= digits:
                used.append(int(value))
        return max(used) + 1

    def _brbank_nosso_numero_sequence(self, digits):
        self.ensure_one()
        provider = self.sudo()
        if not provider.brbank_nosso_numero_sequence_id:
            provider.brbank_nosso_numero_sequence_id = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    {
                        "name": _("Nosso numero: %s", provider.name),
                        # A PostgreSQL sequence: a number taken is never given
                        # again, even if the transaction that took it is undone.
                        "implementation": "standard",
                        "padding": 0,
                        "number_increment": 1,
                        "number_next": provider._brbank_nosso_numero_start(digits),
                        "company_id": provider.company_id.id,
                    }
                )
            )
        return provider.brbank_nosso_numero_sequence_id

    def _brbank_next_nosso_numero(self):
        """Take the next nosso numero of the provider.

        :return: The number as text, or None when the bank numbers the title.
        :raise UserError: When the sequence passed the digits of the bank.
            Never truncated: a truncated number could repeat an old one.
        """
        self.ensure_one()
        digits = self._brbank_nosso_numero_digits()
        if not digits:
            return None
        sequence = self._brbank_nosso_numero_sequence(digits)
        number = sequence.next_by_id()
        if not number.isdigit() or len(number) > digits:
            raise UserError(
                _(
                    "The nosso numero sequence of the provider %(name)s reached "
                    "%(number)s, beyond the %(digits)s digits the bank accepts. "
                    "Agree with the bank on a new wallet or agreement before "
                    "issuing more boletos.",
                    name=self.name,
                    number=number,
                    digits=digits,
                )
            )
        return number

    def _brbank_nosso_numero_callback(self, outcome):
        """The `gerar_nosso_numero` function given to the adapter.

        It runs in the thread of the bank call, so it only reads the numbers
        reserved beforehand by the transactions (context key
        `brbank_nosso_numeros`, by idempotency key).

        :return: The function, or None to keep the library default.
        """
        self.ensure_one()
        if not self._brbank_nosso_numero_digits():
            return None
        numbers = dict(self.env.context.get(NOSSO_NUMERO_CONTEXT) or {})

        def generate(titulo):
            number = numbers.get(titulo.chave_idempotencia)
            if not number:
                raise Validacao("no nosso numero reserved for this title")
            return number

        return generate

    # === BUSINESS METHODS: CALLBACKS === #

    def _brbank_refresh_token_callback(self, outcome):
        """The `ao_renovar_refresh_token` function given to the adapter.

        The bank (BTG) may return a new refresh token at each renewal and
        invalidate the old one. The function runs in the thread of the bank
        call and commits the token at once in a cursor of its own (see
        `_save_refresh_token`): a rollback of the calling transaction, a later
        error of the same call or an exception in the caller never loses it.
        A savepoint would not do: it is undone with the transaction around it.

        :param dict outcome: Receives the token and, when it could not be
            committed apart, why; read by `_brbank_after_call` in the calling
            thread.
        """
        self.ensure_one()
        registry = self.env.registry
        provider_id = self.id

        def renew(token):
            outcome["refresh_token"] = token
            # Stays if the save below raises: the caller then writes it.
            outcome["refresh_token_unsaved"] = "interrupted"
            outcome["refresh_token_unsaved"] = _save_refresh_token(
                registry, provider_id, token
            )

        return renew

    def _brbank_after_call(self, outcome):
        """Apply in the calling transaction what the callbacks reported.

        - Token committed apart: this transaction still reads the old value
          (repeatable read snapshot), and writing the row here would fail with
          a serialization error. The new token stays in `cr.cache` for the
          next calls of the same transaction, until it ends.
        - Token not committed apart (provider not committed yet, or row locked
          by this or another transaction): written in this transaction, the
          only place left; logged, because a rollback here would lose it.
        """
        self.ensure_one()
        token = outcome.get("refresh_token")
        if not token:
            return
        reason = outcome.get("refresh_token_unsaved")
        if not reason:
            cr = self.env.cr
            renewed = cr.cache.setdefault(RENEWED_TOKENS, {})
            if not renewed:

                def forget():
                    cr.cache.pop(RENEWED_TOKENS, None)

                cr.postcommit.add(forget)
                cr.postrollback.add(forget)
            renewed[self.id] = token
            return
        _logger.warning(
            "brbank: provider %s: the renewed refresh token is saved in the "
            "current transaction only (%s); a rollback loses it",
            self.id,
            reason,
        )
        self.sudo().brbank_refresh_token = token

    def _brbank_parse_webhook(self, body, headers):
        """Turn a webhook call into canonical events, without network."""
        self.ensure_one()
        return self._brbank_run(lambda adapter: adapter.parse_webhook(body, headers))

    # === ACTIONS === #

    def action_brbank_rotate_webhook_token(self):
        """Issue a new webhook token: the old URL stops working at once."""
        self.ensure_one()
        self.check_access_rights("write")
        self.sudo().brbank_webhook_token = secrets.token_urlsafe(32)

    def action_brbank_fill_settings_template(self):
        """Add to the JSON fields the keys the adapter needs, keeping values."""
        self.ensure_one()
        provider = self.sudo()
        adapter_class = provider._brbank_adapter_class()
        if not adapter_class:
            raise UserError(_("Choose the bank adapter first."))
        public = provider._brbank_load_json("brbank_extra_config")
        secret = provider._brbank_load_json("brbank_secret_config")
        config_cls = brbank_config.config_class(adapter_class)
        for key in brbank_config.describe(config_cls):
            if key["generic"] or key["callable"]:
                continue
            target = secret if key["secret"] else public
            if key["name"] not in public and key["name"] not in secret:
                target[key["name"]] = brbank_config.placeholder(key)
        provider.write(
            {
                "brbank_extra_config": json.dumps(public, indent=2, sort_keys=True),
                "brbank_secret_config": json.dumps(secret, indent=2, sort_keys=True),
            }
        )
