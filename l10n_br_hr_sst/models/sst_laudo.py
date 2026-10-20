# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TIPO_LAUDO = [
    ("pgr", "PGR - Programa de Gerenciamento de Riscos (NR-1)"),
    ("ltcat", "LTCAT - Laudo Técnico de Condições Ambientais do Trabalho"),
    ("pcmso", "PCMSO - Programa de Controle Médico de Saúde Ocupacional (NR-7)"),
    ("aet", "AET - Análise Ergonômica do Trabalho (NR-17)"),
    ("outro", "Outro"),
]


class L10nBrSstLaudo(models.Model):
    """Laudo que dá origem documental ao risco (PGR, LTCAT, PCMSO, AET).

    O laudo é o que sustenta, perante fiscalização e Justiça do Trabalho, tanto
    o S-2240 quanto o pagamento de insalubridade e periculosidade. Por isso o
    risco aponta para ele, e não o contrário.
    """

    _name = "l10n_br.sst.laudo"
    _description = "SST - Laudo (PGR, LTCAT, PCMSO, AET)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc, id desc"

    name = fields.Char(
        string="Identificação",
        required=True,
        tracking=True,
    )
    tipo = fields.Selection(
        TIPO_LAUDO,
        required=True,
        default="pgr",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("vigente", "Vigente"),
            ("substituido", "Substituído"),
            ("cancelled", "Cancelado"),
        ],
        string="Situação",
        default="draft",
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        string="Início da Vigência",
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string="Fim da Vigência",
        tracking=True,
        help="Vazio significa vigência em aberto.",
    )
    responsavel_id = fields.Many2one(
        "l10n_br.sst.responsavel",
        string="Responsável Técnico",
        tracking=True,
    )
    ambiente_ids = fields.Many2many(
        "l10n_br.sst.ambiente",
        string="Ambientes Cobertos",
        compute="_compute_ambiente_ids",
        store=True,
    )
    risco_ids = fields.One2many(
        "l10n_br.sst.risco",
        "laudo_id",
        string="Fatores de Risco",
    )
    risco_count = fields.Integer(
        string="Riscos",
        compute="_compute_risco_count",
    )
    laudo_anterior_id = fields.Many2one(
        "l10n_br.sst.laudo",
        string="Laudo Substituído",
    )
    observacao = fields.Text(string="Observações")

    @api.depends("risco_ids.ambiente_id")
    def _compute_ambiente_ids(self):
        for rec in self:
            rec.ambiente_ids = rec.risco_ids.mapped("ambiente_id")

    @api.depends("risco_ids")
    def _compute_risco_count(self):
        for rec in self:
            rec.risco_count = len(rec.risco_ids)

    @api.constrains("date_from", "date_to")
    def _check_vigencia(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(
                    _("Laudo %(nome)s: o fim da vigência é anterior ao início.")
                    % {"nome": rec.name}
                )

    def action_vigente(self):
        """Coloca o laudo em vigor e encerra o laudo que ele substitui."""
        for rec in self:
            if not rec.risco_ids:
                raise ValidationError(
                    _(
                        "Laudo %(nome)s: não é possível colocar em vigor um "
                        "laudo sem nenhum fator de risco inventariado. Se o "
                        "ambiente não tem exposição, registre o risco com o "
                        "código de ausência de agente nocivo."
                    )
                    % {"nome": rec.name}
                )
            anterior = rec.laudo_anterior_id
            if anterior and anterior.state == "vigente":
                anterior.write(
                    {
                        "state": "substituido",
                        "date_to": anterior.date_to
                        or fields.Date.subtract(rec.date_from, days=1),
                    }
                )
            rec.state = "vigente"

    def action_cancelar(self):
        self.write({"state": "cancelled"})

    def action_voltar_rascunho(self):
        self.write({"state": "draft"})

    def action_view_riscos(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_br_hr_sst.l10n_br_sst_risco_action"
        )
        action["domain"] = [("laudo_id", "=", self.id)]
        action["context"] = {"default_laudo_id": self.id}
        return action
