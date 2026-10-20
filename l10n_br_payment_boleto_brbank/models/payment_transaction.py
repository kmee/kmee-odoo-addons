# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import re
from decimal import Decimal

from brbank import Encargos, Endereco, Pessoa, StatusCanonico, Titulo
from brbank.erros import Duplicado, ErroBrbank, Indisponivel
from pydantic import ValidationError as PydanticValidationError

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round

from .payment_provider import BRBANK, NOSSO_NUMERO_CONTEXT

_logger = logging.getLogger(__name__)

# O2: canonical status of the bank -> state of the transaction.
STATUS_TO_STATE = {
    StatusCanonico.PENDENTE_REGISTRO: "pending",
    StatusCanonico.REGISTRADO: "authorized",
    StatusCanonico.LIQUIDADO: "done",
    StatusCanonico.BAIXADO: "cancel",
    StatusCanonico.REJEITADO: "error",
}
# Source states each target state accepts (the `payment` rules, minus the
# moves that would undo a payment: a `done` transaction never goes back).
ALLOWED_SOURCES = {
    "pending": ("draft",),
    "authorized": ("draft", "pending"),
    "done": ("draft", "pending", "authorized", "error"),
    "cancel": ("draft", "pending", "authorized"),
    "error": ("draft", "pending", "authorized"),
}
REGISTERED_FIELDS = (
    ("nosso_numero", "our_number"),
    ("linha_digitavel", "digitable_line"),
    ("codigo_barras", "barcode"),
    ("pix_copia_cola", "pix_copia_cola"),
    ("txid", "txid"),
)
TECHNICAL_INFO_LIMIT = 4000


def _percent(value):
    """Odoo keeps 2% as 0.02 (percentage widget); the library wants 2."""
    if not value:
        return None
    return Decimal(str(float_round(value * 100, precision_digits=4)))


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pix_copia_cola = fields.Text(string="Pix Copy and Paste", readonly=True, copy=False)
    txid = fields.Char(string="Pix TXID", readonly=True, copy=False, index=True)
    brbank_idempotency_key = fields.Char(
        string="Idempotency Key",
        readonly=True,
        copy=False,
        index=True,
        help="Key sent to the bank with the registration: repeating the call "
        "with the same key never creates a second title.",
    )
    brbank_seu_numero = fields.Char(
        string="Our Reference at the Bank", readonly=True, copy=False
    )
    brbank_nosso_numero = fields.Char(
        string="Nosso Numero Sent",
        readonly=True,
        copy=False,
        help="Taken from the sequence of the provider before the first "
        "registration call and sent again on every retry of this title.",
    )
    brbank_bank_status = fields.Char(string="Bank Status", readonly=True, copy=False)
    brbank_paid_amount = fields.Monetary(
        string="Amount Paid at the Bank",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    brbank_paid_date = fields.Date(string="Payment Date", readonly=True, copy=False)
    brbank_last_check = fields.Datetime(
        string="Last Bank Check", readonly=True, copy=False
    )
    brbank_instruction_ids = fields.One2many(
        comodel_name="l10n_br.boleto.instruction",
        inverse_name="transaction_id",
        string="Bank Instructions",
    )
    brbank_supports_pdf = fields.Boolean(related="provider_id.brbank_supports_pdf")
    brbank_supports_instruction = fields.Boolean(
        related="provider_id.brbank_supports_instruction"
    )
    brbank_supports_write_off = fields.Boolean(
        related="provider_id.brbank_supports_write_off"
    )

    _sql_constraints = [
        (
            "brbank_idempotency_key_unique",
            "unique(brbank_idempotency_key)",
            "The idempotency key of a bank title must be unique.",
        )
    ]

    # === BUSINESS METHODS: TITLE === #

    def _brbank_new_idempotency_key(self, suffix):
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        return f"odoo-{(dbuuid or '')[:8]}-{suffix}"

    def _brbank_partner(self):
        self.ensure_one()
        partner = self.invoice_ids[:1].partner_id or self.partner_id
        return partner.commercial_partner_id

    def _brbank_prepare_payer(self):
        """The payer of the title, from the commercial partner.

        :raise UserError: Listing the missing fields by name only: the error
            reaches the user and the log, so no personal data goes in it.
        """
        self.ensure_one()
        partner = self._brbank_partner()
        document = re.sub(r"[^0-9A-Za-z]", "", partner.cnpj_cpf or partner.vat or "")
        street = partner.street_name or partner.street
        city = partner.city_id.name or partner.city
        zip_code = re.sub(r"\D", "", partner.zip or "")
        missing = [
            label
            for label, value in (
                (_("CPF/CNPJ"), document),
                (_("Street"), street),
                (_("ZIP code"), len(zip_code) == 8),
                (_("City"), city),
                (_("State"), partner.state_id.code),
            )
            if not value
        ]
        if missing:
            raise UserError(
                _(
                    "The customer of the transaction %(ref)s is missing data the "
                    "bank requires: %(fields)s.",
                    ref=self.reference,
                    fields=", ".join(missing),
                )
            )
        address = Endereco(
            logradouro=street,
            numero=partner.street_number or "SN",
            complemento=partner.street2 or "",
            bairro=partner.district or "",
            cidade=city,
            uf=partner.state_id.code,
            cep=zip_code,
        )
        return Pessoa(
            nome=partner.legal_name or partner.name,
            documento=document,
            endereco=address,
            email=partner.email or None,
        )

    def _brbank_prepare_titulo(self):
        """Build the canonical title (`brbank.Titulo`) of the transaction.

        Money crosses the border as text, never as a binary float.
        """
        self.ensure_one()
        mode = self.invoice_ids[:1].payment_mode_id
        due_date = self.due_date or self.move_line_id.date_maturity
        if not due_date:
            raise UserError(
                _("The transaction %s has no due date for the boleto.", self.reference)
            )
        messages = tuple(
            line.strip()
            for line in (self.boleto_instructions or "").splitlines()
            if line.strip()
        )
        try:
            return Titulo(
                chave_idempotencia=self.brbank_idempotency_key,
                seu_numero=self.brbank_seu_numero or str(self.id),
                valor=Decimal(f"{self.currency_id.round(self.amount):.2f}"),
                vencimento=due_date,
                pagador=self._brbank_prepare_payer(),
                encargos=Encargos(
                    multa_percentual=_percent(
                        self.boleto_penalty or mode.payment_boleto_penalty
                    ),
                    juros_mensal_percentual=_percent(
                        self.boleto_interest or mode.payment_boleto_interest
                    ),
                ),
                mensagens=messages,
            )
        except PydanticValidationError as error:
            # The pydantic message quotes the input: keep only the field names.
            names = sorted(
                {".".join(str(part) for part in item["loc"]) for item in error.errors()}
            )
            raise UserError(
                _(
                    "The bank title of the transaction %(ref)s has invalid data: "
                    "%(fields)s.",
                    ref=self.reference,
                    fields=", ".join(names),
                )
            ) from None

    def _brbank_register(self, raise_on_error=True):
        """Register the title at the bank, once.

        - Already registered (provider reference set): nothing to do.
        - `Duplicado`: the bank already has it, so the title is read back.
        - `Indisponivel`: the transaction stays in draft with the key, and the
          reconciliation cron tries again with the same key.
        - `Validacao`: clear error to the user, or the transaction in error
          when called by the cron (`raise_on_error=False`).

        :return: Whether the title is registered.
        :rtype: bool
        """
        self.ensure_one()
        if self.provider_code != BRBANK or self.provider_reference:
            return bool(self.provider_reference)
        if not self.brbank_idempotency_key:
            self.brbank_idempotency_key = self._brbank_new_idempotency_key(
                f"tx{self.id}"
            )
        try:
            self._brbank_reserve_nosso_numero()
            titulo = self._brbank_prepare_titulo()
        except UserError as error:
            if raise_on_error:
                raise
            self._set_error(error.args[0])
            return False
        provider = self.provider_id
        if self.brbank_nosso_numero:
            provider = provider.with_context(
                **{
                    NOSSO_NUMERO_CONTEXT: {
                        titulo.chave_idempotencia: self.brbank_nosso_numero
                    }
                }
            )
        try:
            try:
                registered = provider._brbank_run(
                    lambda adapter: adapter.registrar_titulo(titulo)
                )
            except Duplicado as error:
                if not error.id_banco:
                    raise
                bank_id = error.id_banco
                registered = provider._brbank_run(
                    lambda adapter: adapter.consultar_titulo(bank_id)
                )
        except Indisponivel as error:
            _logger.info(
                "brbank: bank unavailable registering %s, will retry", self.reference
            )
            self.state_message = _(
                "The bank is unavailable, the registration will be retried: %s",
                error,
            )
            return False
        except ErroBrbank as error:
            message = _(
                "The bank refused the boleto of the transaction %(ref)s: %(error)s",
                ref=self.reference,
                error=error,
            )
            if raise_on_error:
                raise UserError(message) from None
            self._set_error(message)
            return False
        self._brbank_apply_registered(registered)
        if self.brbank_supports_pdf and not self.boleto_pdf:
            self._brbank_fetch_pdf()
        return True

    def _brbank_reserve_nosso_numero(self):
        """Keep on the transaction the nosso numero of its title.

        Taken once, before the first call to the bank, and stored here: a
        retry of the same title (same idempotency key) sends the same number.
        A new attempt for the installment is a new transaction, with a new
        number.
        """
        self.ensure_one()
        if self.brbank_nosso_numero:
            return self.brbank_nosso_numero
        number = self.provider_id._brbank_next_nosso_numero()
        if number:
            self.brbank_nosso_numero = number
        return number

    def _brbank_fetch_pdf(self):
        """Download the boleto PDF when the bank provides it. Not fatal."""
        self.ensure_one()
        reference = self.provider_reference
        try:
            pdf = self.provider_id._brbank_run(
                lambda adapter: adapter.obter_pdf(reference)
            )
        except ErroBrbank as error:
            _logger.info(
                "brbank: no PDF for %s (%s)", self.reference, type(error).__name__
            )
            return False
        self.boleto_pdf = base64.b64encode(pdf)
        return True

    def _brbank_sync_from_bank(self):
        """Read the title back from the bank and apply its status.

        The bank query is the only source of truth: neither a webhook nor a
        return file settles a transaction without it.

        :raise brbank.erros.ErroBrbank: For the caller to handle.
        """
        self.ensure_one()
        if self.provider_code != BRBANK or not self.provider_reference:
            return False
        reference = self.provider_reference
        registered = self.provider_id._brbank_run(
            lambda adapter: adapter.consultar_titulo(reference)
        )
        self._brbank_apply_registered(registered)
        return True

    def _brbank_apply_registered(self, registered):
        """Copy a `TituloRegistrado` of the bank to the transaction."""
        self.ensure_one()
        values = {
            "provider_reference": registered.id_banco,
            "brbank_bank_status": registered.status.value,
            "brbank_last_check": fields.Datetime.now(),
            "is_boleto_payment": True,
        }
        for attribute, field_name in REGISTERED_FIELDS:
            value = getattr(registered, attribute)
            if value:
                values[field_name] = value
        if registered.valor_pago is not None:
            values["brbank_paid_amount"] = float(registered.valor_pago)
        if registered.data_pagamento:
            values["brbank_paid_date"] = registered.data_pagamento
        if registered.resposta_bruta:
            # Masked by the library: no personal data, no secret.
            values["provider_technical_info"] = json.dumps(
                registered.resposta_bruta, default=str, sort_keys=True
            )[:TECHNICAL_INFO_LIMIT]
        self.write(values)
        self._brbank_apply_status(registered.status)

    def _brbank_apply_status(self, status):
        """Move the transaction to the state of the canonical status (O2).

        Called only with a status read from the bank (registration or query).
        """
        self.ensure_one()
        target = STATUS_TO_STATE[StatusCanonico(status)]
        if self.state == target or self.state not in ALLOWED_SOURCES[target]:
            return False
        if target == "pending":
            self._set_pending()
        elif target == "authorized":
            self._set_authorized()
        elif target == "done":
            paid = self.brbank_paid_amount
            if paid and self.currency_id.compare_amounts(paid, self.amount) > 0:
                # Interest and penalty paid: the payment carries what the bank
                # credited, and the base keeps the excess open on it.
                self.amount = paid
            self._set_done()
            self._finalize_post_processing()
        elif target == "cancel":
            self._set_canceled(_("Written off at the bank."))
        else:
            self._set_error(_("The bank rejected the boleto."))
        return True

    # === CRON === #

    def _cron_brbank_reconcile(self, limit=200):
        """Safety net for the webhooks (O8), for every brbank provider.

        1. Registers again the titles left in draft by an unavailable bank,
           with the same idempotency key.
        2. Reads back the open titles, oldest check first, so a run that hits
           the limit continues where the last one stopped.

        Each transaction runs in its own savepoint: a failure does not undo
        the others.
        """
        drafts = self.search(
            [
                ("provider_code", "=", BRBANK),
                ("provider_id.state", "!=", "disabled"),
                ("state", "=", "draft"),
                ("provider_reference", "=", False),
                ("brbank_idempotency_key", "!=", False),
            ],
            limit=limit,
        )
        for tx in drafts:
            tx._brbank_cron_step(lambda t: t._brbank_register(raise_on_error=False))
        open_txs = self.search(
            [
                ("provider_code", "=", BRBANK),
                ("provider_id.state", "!=", "disabled"),
                ("state", "in", ("pending", "authorized")),
                ("provider_reference", "!=", False),
            ],
            order="brbank_last_check, id",
            limit=limit,
        )
        for tx in open_txs:
            tx._brbank_cron_step(lambda t: t._brbank_sync_from_bank())

    def _brbank_cron_step(self, step):
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                step(self)
        except (ErroBrbank, UserError) as error:
            _logger.info(
                "brbank: %s skipped by the reconciliation cron (%s)",
                self.reference,
                type(error).__name__,
            )
            if isinstance(error, Indisponivel):
                return
            self.brbank_last_check = fields.Datetime.now()

    # === BUSINESS METHODS: CNAB BRIDGE (O10) === #

    def _brbank_find_by_our_number(self, our_number, company=None):
        """The live brbank transaction of a nosso numero, for return files."""
        domain = [
            ("provider_code", "=", BRBANK),
            ("state", "in", ("pending", "authorized")),
            "|",
            ("our_number", "=", our_number),
            ("provider_reference", "=", our_number),
        ]
        if company:
            domain.append(("company_id", "=", company.id))
        return self.search(domain, limit=1)

    def _brbank_notify_cnab_occurrence(self, our_number, company=None):
        """Hook for a CNAB return of an account that also uses the API (O10).

        The return file only says "something happened": the transaction is
        read back from the bank, so the API and the file cannot settle the
        same title twice nor disagree.

        :return: The transaction found, if any.
        """
        tx = self._brbank_find_by_our_number(our_number, company=company)
        if tx:
            tx._brbank_sync_from_bank()
        return tx

    # === PAYMENT FLOW === #

    def _send_capture_request(self):
        """Override of `payment`: "capture" reads the title back from the bank.

        Note: self.ensure_one()
        """
        res = super()._send_capture_request()
        if self.provider_code == BRBANK:
            self.action_brbank_check_status()
        return res

    def _send_void_request(self):
        """Override of `payment`: "void" writes the title off at the bank.

        Note: self.ensure_one()
        """
        res = super()._send_void_request()
        if self.provider_code == BRBANK:
            self.action_brbank_write_off()
        return res

    # === ACTIONS === #

    def _brbank_raise_user_error(self, error):
        raise UserError(
            _(
                "The bank could not handle the request for %(ref)s: %(error)s",
                ref=self.reference,
                error=error,
            )
        ) from None

    def action_brbank_register(self):
        for tx in self:
            tx._brbank_register()

    def action_brbank_check_status(self):
        for tx in self:
            try:
                tx._brbank_sync_from_bank()
            except ErroBrbank as error:
                tx._brbank_raise_user_error(error)

    def action_brbank_download_pdf(self):
        self.ensure_one()
        if not self.boleto_pdf:
            if not (self.brbank_supports_pdf and self.provider_reference):
                raise UserError(_("The bank does not provide the boleto PDF."))
            if not self._brbank_fetch_pdf():
                raise UserError(_("The boleto PDF is not available yet."))
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/payment.transaction/{self.id}/boleto_pdf/"
                f"boleto-{self.id}.pdf?download=true"
            ),
            "target": "new",
        }

    def action_brbank_new_instruction(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Bank Instruction"),
            "res_model": "l10n_br.boleto.instruction",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transaction_id": self.id},
        }

    def action_brbank_write_off(self):
        self.ensure_one()
        instruction = self.env["l10n_br.boleto.instruction"].create(
            {"transaction_id": self.id, "command": "baixa"}
        )
        return instruction.action_send()
