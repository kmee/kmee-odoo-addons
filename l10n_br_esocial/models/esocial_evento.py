from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def action_mark_error(self):
        for rec in self:
            rec.state = "error"

    def action_mark_success(self):
        for rec in self:
            rec.state = "success"
