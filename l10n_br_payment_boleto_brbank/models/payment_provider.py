# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from brbank import Capacidade, registro
from brbank.erros import AdapterNaoEncontrado, Validacao

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_br_bank_connection.models.connection import (
    ADAPTER_LABELS,
    PIX_PROFILE_LABELS,
    capability_flag_labels,
)
from odoo.addons.l10n_br_bank_connection.utils import config as brbank_config

_logger = logging.getLogger(__name__)

BRBANK = "brbank"
# Alias route of the webhook, kept for the URLs already registered at the banks
# before the connection took the webhook over.
WEBHOOK_ROUTE = "/payment/brbank/webhook"
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

    brbank_connection_id = fields.Many2one(
        comodel_name="l10n_br_bank_connection.connection",
        string="Bank Connection",
        domain="[('adapter', '=', brbank_adapter)]",
        ondelete="restrict",
        index=True,
        help="Credentials, token and webhook of the bank account this provider "
        "uses. One connection can serve several providers (boleto and Pix, "
        "for instance).",
    )
    brbank_nosso_numero_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Nosso Numero Sequence",
        readonly=True,
        copy=False,
        help="Created at the first title of a bank whose nosso numero is "
        "chosen by the issuer. Numbers are never reused.",
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
    brbank_is_pix = fields.Boolean(compute="_compute_brbank_adapter_info")
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
        labels = capability_flag_labels()
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
            provider.brbank_is_pix = "perfil" in keys

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
        "brbank_connection_id",
    )
    def _check_brbank_configuration(self):
        for provider in self.sudo():
            if provider.code != BRBANK or provider.state == "disabled":
                continue
            if not provider.brbank_adapter:
                raise ValidationError(_("Choose the bank adapter of the provider."))
            connection = provider.brbank_connection_id
            if not connection:
                raise ValidationError(
                    _("Choose the bank connection of the provider %s.", provider.name)
                )
            if connection.adapter != provider.brbank_adapter:
                raise ValidationError(
                    _(
                        "The connection %(connection)s uses another bank adapter "
                        "than the provider %(provider)s.",
                        connection=connection.name,
                        provider=provider.name,
                    )
                )
            try:
                provider._brbank_prepare_adapter()
            except UserError as error:
                raise ValidationError(error.args[0]) from error

    @api.onchange("brbank_connection_id")
    def _onchange_brbank_connection_id(self):
        connection = self.brbank_connection_id
        if connection:
            self.brbank_adapter = connection.adapter
            self.brbank_pix_perfil = connection.pix_profile

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

    def _brbank_connection(self):
        """The bank connection of the provider, as the system.

        :raise UserError: If the provider is not a brbank provider or has no
            connection yet.
        """
        self.ensure_one()
        if self.code != BRBANK or not self.brbank_adapter:
            raise UserError(_("This provider is not a brbank provider."))
        connection = self.sudo().brbank_connection_id
        if not connection:
            raise UserError(
                _("The payment provider %s has no bank connection.", self.name)
            )
        return connection

    def _brbank_callbacks(self):
        """Callable keys of the adapter configuration this provider serves."""
        self.ensure_one()
        callback = self._brbank_nosso_numero_callback()
        return {"gerar_nosso_numero": callback} if callback else {}

    def _brbank_prepare_adapter(self, callback_outcome=None):
        """Build the adapter class and configuration of the connection.

        :param dict callback_outcome: Filled by the refresh token callback of
            the connection.
        :return: The adapter class and its configuration.
        :rtype: tuple
        :raise UserError: If the configuration is incomplete.
        """
        self.ensure_one()
        return self._brbank_connection()._l10n_br_bank_prepare_adapter(
            callbacks=self._brbank_callbacks(), outcome=callback_outcome
        )

    def _brbank_run(self, operation):
        """Call the bank through the connection of the provider.

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
        return self._brbank_connection()._l10n_br_bank_run(
            operation, callbacks=self._brbank_callbacks()
        )

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

    def _brbank_nosso_numero_callback(self):
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
