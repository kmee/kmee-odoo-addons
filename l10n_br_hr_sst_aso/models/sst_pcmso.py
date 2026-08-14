# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Periodicidade padrão do exame periódico da NR-7, em meses. A norma admite
# periodicidade menor conforme o risco e a faixa etária, por isso o valor é
# parametrizável por programa e por faixa.
PERIODICIDADE_PADRAO_MESES = 12


class L10nBrSstPcmso(models.Model):
    """Programa de Controle Médico de Saúde Ocupacional (NR-7).

    O PCMSO define quem é o médico coordenador e de quanto em quanto tempo cada
    trabalhador faz o exame periódico. É dele que sai o agendamento automático
    dos ASOs e o relatório analítico anual.
    """

    _name = "l10n_br.sst.pcmso"
    _description = "SST - PCMSO"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc"

    name = fields.Char(
        string="Identificação",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    nr_insc = fields.Char(
        string="Estabelecimento",
        size=14,
        help="Inscrição do estabelecimento coberto pelo programa. Vazio "
        "significa todos os estabelecimentos da empresa.",
    )
    medico_coordenador_id = fields.Many2one(
        "l10n_br.sst.responsavel",
        string="Médico Coordenador",
        required=True,
        tracking=True,
        domain=[("ide_oc", "=", "1")],
        help="Médico do trabalho que coordena o programa (CRM).",
    )
    date_from = fields.Date(
        string="Início da Vigência",
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string="Fim da Vigência",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("vigente", "Vigente"),
            ("encerrado", "Encerrado"),
        ],
        string="Situação",
        default="draft",
        required=True,
        tracking=True,
    )
    periodicidade_meses = fields.Integer(
        string="Periodicidade Padrão (meses)",
        default=PERIODICIDADE_PADRAO_MESES,
        required=True,
        help="Intervalo padrão entre exames periódicos. Faixas específicas "
        "sobrescrevem este valor.",
    )
    faixa_ids = fields.One2many(
        "l10n_br.sst.pcmso.faixa",
        "pcmso_id",
        string="Periodicidade por Faixa",
    )
    exame_ids = fields.One2many(
        "hr.employee.medical.examination",
        "l10n_br_pcmso_id",
        string="Exames",
    )
    exame_count = fields.Integer(
        string="Exames",
        compute="_compute_exame_count",
    )
    relatorio_anual = fields.Text(
        string="Relatório Analítico Anual",
        help="Relatório analítico exigido pela NR-7, item 7.6.",
    )

    @api.depends("exame_ids")
    def _compute_exame_count(self):
        for rec in self:
            rec.exame_count = len(rec.exame_ids)

    @api.constrains("date_from", "date_to")
    def _check_vigencia(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(
                    _("PCMSO %(nome)s: o fim da vigência é anterior ao início.")
                    % {"nome": rec.name}
                )

    @api.constrains("periodicidade_meses")
    def _check_periodicidade(self):
        for rec in self:
            if rec.periodicidade_meses <= 0:
                raise ValidationError(
                    _("PCMSO %(nome)s: a periodicidade deve ser positiva.")
                    % {"nome": rec.name}
                )

    def action_vigente(self):
        self.write({"state": "vigente"})

    def action_encerrar(self):
        self.write({"state": "encerrado"})

    @api.model
    def buscar_vigente(self, company, data=None):
        """PCMSO vigente da empresa na data informada."""
        data = data or fields.Date.context_today(self)
        return self.search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "vigente"),
                ("date_from", "<=", data),
                "|",
                ("date_to", "=", False),
                ("date_to", ">=", data),
            ],
            order="date_from desc",
            limit=1,
        )

    def periodicidade_do_empregado(self, employee, data=None):
        """Intervalo em meses até o próximo exame periódico do trabalhador.

        Aplica a faixa mais específica que couber (idade e exposição a risco);
        na ausência de faixa, vale a periodicidade padrão do programa.
        """
        self.ensure_one()
        data = data or fields.Date.context_today(self)
        idade = employee._l10n_br_sst_idade(data)
        exposto = bool(employee._l10n_br_sst_riscos_vigentes(data))
        for faixa in self.faixa_ids.sorted("meses"):
            if faixa.exige_exposicao and not exposto:
                continue
            if faixa.idade_de and (idade is None or idade < faixa.idade_de):
                continue
            if faixa.idade_ate and (idade is None or idade > faixa.idade_ate):
                continue
            return faixa.meses
        return self.periodicidade_meses


class L10nBrSstPcmsoFaixa(models.Model):
    """Periodicidade de exame periódico por faixa etária e exposição (NR-7)."""

    _name = "l10n_br.sst.pcmso.faixa"
    _description = "SST - Faixa de Periodicidade do PCMSO"
    _order = "meses"

    pcmso_id = fields.Many2one(
        "l10n_br.sst.pcmso",
        string="PCMSO",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Descrição",
        required=True,
    )
    idade_de = fields.Integer(string="Idade de")
    idade_ate = fields.Integer(string="Idade até")
    exige_exposicao = fields.Boolean(
        string="Somente Expostos a Risco",
        help="Aplica a faixa apenas a quem tem fator de risco vigente.",
    )
    meses = fields.Integer(
        string="Periodicidade (meses)",
        required=True,
        default=12,
    )

    @api.constrains("meses")
    def _check_meses(self):
        for rec in self:
            if rec.meses <= 0:
                raise ValidationError(
                    _("Faixa %(nome)s: a periodicidade deve ser positiva.")
                    % {"nome": rec.name}
                )
