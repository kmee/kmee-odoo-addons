# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ESocialEvento(models.Model):
    _name = "l10n_br.esocial.evento"
    _description = "eSocial - Evento"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(compute="_compute_name", store=True)
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("validated", "Validado"),
            ("pending", "Aguardando"),
            ("sent", "Transmitido"),
            ("success", "Sucesso"),
            ("error", "Erro"),
            ("rectified", "Retificado"),
            ("excluded", "Excluído"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )
    tipo = fields.Char(
        string="Tipo Evento",
        size=10,
        required=True,
        index=True,
        help="Ex: S-1000, S-1010, S-1200, S-2200, etc.",
    )
    operacao = fields.Selection(
        [
            ("I", "Inclusão"),
            ("A", "Alteração"),
            ("E", "Exclusão"),
            ("R", "Retificação"),
        ],
        string="Operação",
        default="I",
    )
    id_evento = fields.Char(
        string="ID Evento",
        index=True,
        help="Identificador único do evento gerado pelo sistema.",
    )
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        help="Formato AAAA-MM para eventos periódicos.",
    )
    ind_retif = fields.Selection(
        [
            ("1", "Original"),
            ("2", "Retificação"),
        ],
        string="Indicativo Retificação",
        default="1",
    )
    nr_recibo = fields.Char(
        string="Nº Recibo",
        help="Número do recibo retornado pelo governo.",
    )
    xml_envio = fields.Text(string="XML Envio")
    xml_retorno = fields.Text(string="XML Retorno")
    lote_id = fields.Many2one(
        "l10n_br.esocial.lote",
        string="Lote",
        ondelete="set null",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    origem_model = fields.Char(
        string="Modelo Origem",
        help="Nome do modelo Odoo que originou o evento.",
    )
    origem_id = fields.Integer(
        string="ID Origem",
        help="ID do registro que originou o evento.",
    )
    ocorrencia_ids = fields.One2many(
        "l10n_br.esocial.ocorrencia",
        "evento_id",
        string="Ocorrências",
    )
    evento_excluido_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Evento Excluído",
        ondelete="set null",
        help="Preenchido nos eventos S-3000: aponta o evento que a exclusão " "desfaz.",
    )
    exclusao_evento_id = fields.One2many(
        "l10n_br.esocial.evento",
        "evento_excluido_id",
        string="Exclusões",
    )
    totalizador_ids = fields.One2many(
        "l10n_br.esocial.totalizador",
        "evento_id",
        string="Totalizadores",
        help="Eventos totalizadores (S-5001/S-5002/S-5011/S-5012) devolvidos "
        "pelo governo no processamento deste evento.",
    )
    totalizador_count = fields.Integer(compute="_compute_totalizador_count")

    @api.depends("totalizador_ids")
    def _compute_totalizador_count(self):
        for rec in self:
            rec.totalizador_count = len(rec.totalizador_ids)

    @api.depends("tipo", "id_evento")
    def _compute_name(self):
        for rec in self:
            parts = [rec.tipo or ""]
            if rec.id_evento:
                parts.append(rec.id_evento)
            rec.name = " - ".join(parts)

    def action_validate(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Apenas eventos em rascunho podem ser validados."))
            rec.state = "validated"

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ("validated", "error"):
                raise UserError(
                    _("Apenas eventos validados ou com erro podem voltar a rascunho.")
                )
            rec.state = "draft"

    def registrar_aceite(self, nr_recibo=None, retorno_xml=None):
        """Registra o aceite do evento pelo eSocial.

        Concentra tudo o que depende do aceite: recibo, XML de retorno,
        totalizadores devolvidos e propagação da exclusão (S-3000). É chamado
        pelo processamento do retorno do lote.
        """
        for rec in self:
            vals = {"state": "success"}
            if nr_recibo:
                vals["nr_recibo"] = nr_recibo
            if retorno_xml:
                vals["xml_retorno"] = retorno_xml
            rec.write(vals)
            if retorno_xml:
                rec._consumir_totalizadores(retorno_xml)
            rec._propagar_exclusao()

    def _consumir_totalizadores(self, retorno_xml):
        """Persiste os totalizadores devolvidos no retorno deste evento."""
        self.ensure_one()
        return self.env["l10n_br.esocial.totalizador"].criar_do_retorno(
            self, retorno_xml
        )

    def _propagar_exclusao(self):
        """Marca como excluído o evento que um S-3000 aceito desfez."""
        self.ensure_one()
        if self.tipo != "S-3000" or not self.evento_excluido_id:
            return
        excluido = self.evento_excluido_id
        excluido.write({"state": "excluded"})
        excluido.message_post(
            body=_(
                "Evento excluído no eSocial pelo S-3000 %(nome)s "
                "(recibo %(recibo)s)."
            )
            % {"nome": self.name, "recibo": self.nr_recibo or _("sem recibo")}
        )

    def _check_audit_manager(self):
        """Only payroll managers may force an event state manually."""
        if not self.env.user.has_group("payroll.group_payroll_manager"):
            raise UserError(
                _(
                    "Apenas gestores de folha de pagamento podem forçar "
                    "manualmente o estado de um evento eSocial."
                )
            )

    def action_mark_error(self):
        self._check_audit_manager()
        for rec in self:
            rec.state = "error"
            rec.message_post(
                body=_("Estado forçado manualmente para ERRO por %(user)s.")
                % {"user": self.env.user.name}
            )
            _logger.info(
                "eSocial evento %s: estado forçado para 'error' por %s (uid=%s).",
                rec.id,
                self.env.user.name,
                self.env.uid,
            )

    def action_mark_success(self):
        self._check_audit_manager()
        for rec in self:
            rec.state = "success"
            rec.message_post(
                body=_("Estado forçado manualmente para SUCESSO por %(user)s.")
                % {"user": self.env.user.name}
            )
            _logger.info(
                "eSocial evento %s: estado forçado para 'success' por %s (uid=%s).",
                rec.id,
                self.env.user.name,
                self.env.uid,
            )
