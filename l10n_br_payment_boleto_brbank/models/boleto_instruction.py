# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from decimal import Decimal

from brbank import Instrucao, TipoInstrucao
from brbank.erros import Duplicado, ErroBrbank, Indisponivel, NaoSuportado, Validacao

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .payment_provider import BRBANK

_logger = logging.getLogger(__name__)

COMMANDS = {
    "prorrogacao": TipoInstrucao.PRORROGACAO,
    "abatimento": TipoInstrucao.ABATIMENTO,
    "protesto": TipoInstrucao.PROTESTO,
    "negativacao": TipoInstrucao.NEGATIVACAO,
    "baixa": TipoInstrucao.BAIXA,
}


class BoletoInstruction(models.Model):
    """A command sent to the bank about a registered title (O6).

    One record per command keeps what was asked, the idempotency key sent and
    the answer of the bank (masked by the library).
    """

    _name = "l10n_br.boleto.instruction"
    _description = "Boleto Bank Instruction"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    transaction_id = fields.Many2one(
        comodel_name="payment.transaction",
        string="Transaction",
        required=True,
        ondelete="cascade",
        index=True,
        domain=[("provider_code", "=", BRBANK)],
    )
    provider_id = fields.Many2one(related="transaction_id.provider_id", store=True)
    company_id = fields.Many2one(related="transaction_id.company_id", store=True)
    currency_id = fields.Many2one(related="transaction_id.currency_id")
    command = fields.Selection(
        selection=[
            ("prorrogacao", "Due date extension"),
            ("abatimento", "Rebate"),
            ("protesto", "Protest"),
            ("negativacao", "Credit bureau report"),
            ("baixa", "Write-off"),
        ],
        required=True,
    )
    new_due_date = fields.Date()
    amount = fields.Monetary(string="Rebate Amount", currency_field="currency_id")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Accepted"),
            ("rejected", "Rejected"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        readonly=True,
        copy=False,
    )
    idempotency_key = fields.Char(readonly=True, copy=False, index=True)
    result_message = fields.Char(string="Result", readonly=True, copy=False)
    bank_response = fields.Text(
        readonly=True,
        copy=False,
        groups="base.group_no_one",
        help="Answer of the bank, masked: no personal data, no secret.",
    )

    _sql_constraints = [
        (
            "idempotency_key_unique",
            "unique(idempotency_key)",
            "The idempotency key of a bank instruction must be unique.",
        )
    ]

    @api.depends("transaction_id.reference", "command")
    def _compute_name(self):
        labels = dict(self._fields["command"]._description_selection(self.env))
        for instruction in self:
            instruction.name = "{} - {}".format(
                instruction.transaction_id.reference or "",
                labels.get(instruction.command, ""),
            )

    @api.constrains("command", "new_due_date", "amount")
    def _check_command_values(self):
        for instruction in self:
            if instruction.command == "prorrogacao" and not instruction.new_due_date:
                raise ValidationError(_("A due date extension needs the new date."))
            if instruction.command == "abatimento" and (
                instruction.currency_id.compare_amounts(instruction.amount, 0) <= 0
                or instruction.currency_id.compare_amounts(
                    instruction.amount, instruction.transaction_id.amount
                )
                >= 0
            ):
                raise ValidationError(
                    _("The rebate must be above zero and below the boleto amount.")
                )

    def _required_capability_supported(self):
        """O11: write-off needs `BAIXA`, the other commands `ALTERACAO`."""
        self.ensure_one()
        provider = self.transaction_id.provider_id
        if self.command == "baixa":
            return provider.brbank_supports_write_off
        return provider.brbank_supports_instruction

    def _prepare_instrucao(self):
        self.ensure_one()
        return Instrucao(
            chave_idempotencia=self.idempotency_key,
            tipo=COMMANDS[self.command],
            nova_data_vencimento=self.new_due_date or None,
            valor=Decimal(f"{self.amount:.2f}") if self.amount else None,
        )

    def action_send(self):
        """Send the instruction to the bank and record its answer.

        `NaoSuportado` and `Validacao` reject the instruction with the reason;
        `Indisponivel` keeps it in draft to be sent again; `Duplicado` means
        the bank already applied it, so the title is read back.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only a draft instruction can be sent."))
        transaction = self.transaction_id
        if transaction.provider_code != BRBANK or not transaction.provider_reference:
            raise UserError(_("The boleto is not registered at the bank."))
        if not self._required_capability_supported():
            raise UserError(
                _("The bank of this provider does not accept this instruction.")
            )
        if not self.idempotency_key:
            self.idempotency_key = transaction._brbank_new_idempotency_key(
                f"instr{self.id}"
            )
        reference = transaction.provider_reference
        provider = transaction.provider_id
        try:
            if self.command == "baixa":
                registered = provider._brbank_run(
                    lambda adapter: adapter.baixar_titulo(reference)
                )
            else:
                instrucao = self._prepare_instrucao()
                registered = provider._brbank_run(
                    lambda adapter: adapter.enviar_instrucao(reference, instrucao)
                )
        except Duplicado:
            transaction._brbank_sync_from_bank()
            self.write(
                {
                    "state": "done",
                    "result_message": _("The bank had already applied it."),
                }
            )
            return True
        except Indisponivel as error:
            self.result_message = _("Bank unavailable, send it again later: %s", error)
            return self._notify(self.result_message, "warning")
        except (NaoSuportado, Validacao) as error:
            self._record_failure("rejected", error)
            return self._notify(self.result_message, "danger")
        except ErroBrbank as error:
            self._record_failure("error", error)
            return self._notify(self.result_message, "danger")
        self.write(
            {
                "state": "done",
                "result_message": _("Accepted by the bank."),
                "bank_response": json.dumps(
                    registered.resposta_bruta, default=str, sort_keys=True
                ),
            }
        )
        if self.command == "prorrogacao":
            transaction.due_date = self.new_due_date
        transaction._brbank_apply_registered(registered)
        return True

    def _record_failure(self, state, error):
        self.write(
            {
                "state": state,
                "result_message": str(error),
                "bank_response": json.dumps(
                    getattr(error, "resposta_bruta", None), default=str
                ),
            }
        )

    def _notify(self, message, kind):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": kind, "sticky": False},
        }
