# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CreditAnalysis(models.Model):
    _name = "credit.analysis"
    _description = "Consulta de Credito"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    # Basic fields
    name = fields.Char(
        string="Numero",
        readonly=True,
        copy=False,
        default=lambda self: _("Novo"),
    )
    company_id = fields.Many2one(
        comodel_name="credit.company",
        string="Empresa",
        required=True,
        tracking=True,
    )
    cnpj = fields.Char(
        string="CNPJ",
        related="company_id.cnpj",
        store=True,
    )
    cnpj_input = fields.Char(
        string="Consultar CNPJ",
        help="Digite o CNPJ para iniciar uma consulta rapida",
    )
    date = fields.Datetime(
        string="Data da Consulta",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    date_done = fields.Datetime(
        string="Data de Conclusao",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Analista",
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Rascunho"),
            ("done", "Concluida"),
            ("cancelled", "Cancelada"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    notes = fields.Html(
        string="Observacoes",
    )

    # Score and Risk Analysis (F04)
    score = fields.Integer(
        string="Score",
        default=0,
        tracking=True,
    )
    risk_level = fields.Selection(
        selection=[
            ("very_high", "Muito Alto"),
            ("high", "Alto"),
            ("medium", "Medio"),
            ("low", "Baixo"),
            ("very_low", "Muito Baixo"),
        ],
        string="Nivel de Risco",
        compute="_compute_risk_level",
        store=True,
        tracking=True,
    )
    default_probability = fields.Float(
        string="Probabilidade de Inadimplencia (%)",
        compute="_compute_default_probability",
        store=True,
    )

    # Recommendation
    recommendation = fields.Selection(
        selection=[
            ("approved", "Aprovado"),
            ("caution", "Cautela"),
            ("rejected", "Rejeitado"),
        ],
        string="Recomendacao",
        compute="_compute_recommendation",
        store=True,
        tracking=True,
    )
    recommendation_override = fields.Selection(
        selection=[
            ("approved", "Aprovado"),
            ("caution", "Cautela"),
            ("rejected", "Rejeitado"),
        ],
        string="Override de Recomendacao",
    )
    recommendation_notes = fields.Text(
        string="Justificativa do Override",
    )
    recommendation_final = fields.Selection(
        selection=[
            ("approved", "Aprovado"),
            ("caution", "Cautela"),
            ("rejected", "Rejeitado"),
        ],
        string="Recomendacao Final",
        compute="_compute_recommendation_final",
        store=True,
    )

    # Credit Limit (F04)
    faturamento_faixa = fields.Selection(
        selection=[
            ("mei", "Ate R$ 81.000"),
            ("me_1", "R$ 81.001 a R$ 360.000"),
            ("me_2", "R$ 360.001 a R$ 520.000"),
            ("epp", "R$ 520.001 a R$ 4.800.000"),
            ("medio", "R$ 4.800.001 a R$ 30.000.000"),
            ("grande", "Acima de R$ 30.000.000"),
        ],
        string="Faixa de Faturamento",
    )
    faturamento_estimado = fields.Monetary(
        string="Faturamento Estimado",
        currency_field="currency_id",
    )
    faturamento_medio = fields.Monetary(
        string="Faturamento Medio da Faixa",
        compute="_compute_faturamento_medio",
        currency_field="currency_id",
    )
    limite_credito_sugerido = fields.Monetary(
        string="Limite de Credito Sugerido",
        compute="_compute_limite_credito",
        store=True,
        currency_field="currency_id",
    )
    limite_credito_manual = fields.Monetary(
        string="Limite de Credito Manual",
        currency_field="currency_id",
    )
    limite_credito_final = fields.Monetary(
        string="Limite de Credito Final",
        compute="_compute_limite_credito_final",
        store=True,
        currency_field="currency_id",
    )

    # Payment Behavior (F06)
    pontualidade_score = fields.Integer(
        string="Score de Pontualidade",
        default=0,
        help="Score de 0 a 100 indicando pontualidade nos pagamentos",
    )
    pontualidade_nivel = fields.Selection(
        selection=[
            ("alto", "Alto"),
            ("medio", "Medio"),
            ("baixo", "Baixo"),
        ],
        string="Nivel de Pontualidade",
        compute="_compute_pontualidade_nivel",
        store=True,
    )
    atraso_score = fields.Integer(
        string="Score de Atraso",
        default=0,
        help="Score de 0 a 100 indicando nivel de atraso (maior = mais atraso)",
    )
    atraso_nivel = fields.Selection(
        selection=[
            ("baixo", "Baixo"),
            ("medio", "Medio"),
            ("alto", "Alto"),
        ],
        string="Nivel de Atraso",
        compute="_compute_atraso_nivel",
        store=True,
    )
    media_dias_atraso = fields.Integer(
        string="Media de Dias em Atraso",
        default=0,
    )

    # Currency
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )

    # Restrictions (F05)
    restriction_ids = fields.One2many(
        comodel_name="credit.restriction",
        inverse_name="analysis_id",
        string="Restricoes",
    )
    total_negativacoes = fields.Integer(
        string="Qtd Negativacoes",
        compute="_compute_restriction_totals",
        store=True,
    )
    total_negativacoes_value = fields.Monetary(
        string="Valor Negativacoes",
        compute="_compute_restriction_totals",
        store=True,
        currency_field="currency_id",
    )
    total_protestos = fields.Integer(
        string="Qtd Protestos",
        compute="_compute_restriction_totals",
        store=True,
    )
    total_protestos_value = fields.Monetary(
        string="Valor Protestos",
        compute="_compute_restriction_totals",
        store=True,
        currency_field="currency_id",
    )
    total_acoes = fields.Integer(
        string="Qtd Acoes Judiciais",
        compute="_compute_restriction_totals",
        store=True,
    )
    total_acoes_value = fields.Monetary(
        string="Valor Acoes Judiciais",
        compute="_compute_restriction_totals",
        store=True,
        currency_field="currency_id",
    )
    total_cheques = fields.Integer(
        string="Qtd Cheques",
        compute="_compute_restriction_totals",
        store=True,
    )
    has_falencia = fields.Boolean(
        string="Falencia/Recuperacao Judicial",
        compute="_compute_restriction_totals",
        store=True,
    )
    has_restricoes = fields.Boolean(
        string="Possui Restricoes",
        compute="_compute_restriction_totals",
        store=True,
    )
    total_restricoes_value = fields.Monetary(
        string="Valor Total Restricoes",
        compute="_compute_restriction_totals",
        store=True,
        currency_field="currency_id",
    )

    # Credit History (F07)
    credit_history_ids = fields.One2many(
        comodel_name="credit.history.line",
        inverse_name="analysis_id",
        string="Historico de Credito",
    )
    total_credito_12m = fields.Monetary(
        string="Total Credito 12 meses",
        compute="_compute_credit_history_totals",
        store=True,
        currency_field="currency_id",
    )
    media_credito_12m = fields.Monetary(
        string="Media Credito 12 meses",
        compute="_compute_credit_history_totals",
        store=True,
        currency_field="currency_id",
    )

    # Commitment (F07)
    commitment_ids = fields.One2many(
        comodel_name="credit.commitment.line",
        inverse_name="analysis_id",
        string="Comprometimento Futuro",
    )
    total_comprometido_12m = fields.Monetary(
        string="Total Comprometido 12 meses",
        compute="_compute_commitment_totals",
        store=True,
        currency_field="currency_id",
    )

    # Company related fields for display
    razao_social = fields.Char(
        string="Razao Social",
        related="company_id.razao_social",
    )
    nome_fantasia = fields.Char(
        string="Nome Fantasia",
        related="company_id.nome_fantasia",
    )
    situacao_cadastral = fields.Selection(
        string="Situacao Cadastral",
        related="company_id.situacao_cadastral",
    )
    tempo_mercado = fields.Integer(
        string="Tempo de Mercado",
        related="company_id.tempo_mercado",
    )

    # Partners from company
    partner_ids = fields.One2many(
        string="Socios",
        related="company_id.partner_ids",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Novo")) == _("Novo"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("credit.analysis")
                    or _("Novo")
                )
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            {
                "name": _("Novo"),
                "date": fields.Datetime.now(),
                "date_done": False,
                "user_id": self.env.user.id,
                "state": "draft",
            }
        )
        return super().copy(default)

    @api.depends("score")
    def _compute_risk_level(self):
        for record in self:
            score = record.score
            if score <= 200:
                record.risk_level = "very_high"
            elif score <= 400:
                record.risk_level = "high"
            elif score <= 600:
                record.risk_level = "medium"
            elif score <= 800:
                record.risk_level = "low"
            else:
                record.risk_level = "very_low"

    @api.depends("risk_level")
    def _compute_default_probability(self):
        probabilities = {
            "very_high": 50.0,
            "high": 35.0,
            "medium": 20.0,
            "low": 10.0,
            "very_low": 3.0,
        }
        for record in self:
            record.default_probability = probabilities.get(
                record.risk_level, 0.0
            )

    @api.depends("score", "has_falencia", "has_restricoes")
    def _compute_recommendation(self):
        for record in self:
            if record.score >= 700 and not record.has_falencia:
                record.recommendation = "approved"
            elif record.score >= 400 and not record.has_falencia:
                record.recommendation = "caution"
            else:
                record.recommendation = "rejected"

    @api.depends("recommendation", "recommendation_override")
    def _compute_recommendation_final(self):
        for record in self:
            record.recommendation_final = (
                record.recommendation_override or record.recommendation
            )

    @api.depends("faturamento_faixa")
    def _compute_faturamento_medio(self):
        faixa_valores = {
            "mei": 40500,
            "me_1": 220500,
            "me_2": 440000,
            "epp": 2660000,
            "medio": 17400000,
            "grande": 50000000,
        }
        for record in self:
            record.faturamento_medio = faixa_valores.get(
                record.faturamento_faixa, 0
            )

    @api.depends("score", "faturamento_estimado", "faturamento_medio")
    def _compute_limite_credito(self):
        for record in self:
            base = record.faturamento_estimado or record.faturamento_medio
            if base and record.score:
                # Factor based on score: 0.01 to 0.10
                factor = record.score / 10000.0
                record.limite_credito_sugerido = base * factor
            else:
                record.limite_credito_sugerido = 0

    @api.depends("limite_credito_sugerido", "limite_credito_manual")
    def _compute_limite_credito_final(self):
        for record in self:
            record.limite_credito_final = (
                record.limite_credito_manual or record.limite_credito_sugerido
            )

    @api.depends("pontualidade_score")
    def _compute_pontualidade_nivel(self):
        for record in self:
            score = record.pontualidade_score
            if score >= 70:
                record.pontualidade_nivel = "alto"
            elif score >= 40:
                record.pontualidade_nivel = "medio"
            else:
                record.pontualidade_nivel = "baixo"

    @api.depends("atraso_score")
    def _compute_atraso_nivel(self):
        for record in self:
            score = record.atraso_score
            if score <= 30:
                record.atraso_nivel = "baixo"
            elif score <= 60:
                record.atraso_nivel = "medio"
            else:
                record.atraso_nivel = "alto"

    @api.depends("restriction_ids", "restriction_ids.type", "restriction_ids.value")
    def _compute_restriction_totals(self):
        for record in self:
            restrictions = record.restriction_ids.filtered(
                lambda r: r.state == "active"
            )
            # Negativacoes
            neg = restrictions.filtered(lambda r: r.type == "negativacao")
            record.total_negativacoes = len(neg)
            record.total_negativacoes_value = sum(neg.mapped("value"))
            # Protestos
            prot = restrictions.filtered(lambda r: r.type == "protesto")
            record.total_protestos = len(prot)
            record.total_protestos_value = sum(prot.mapped("value"))
            # Acoes Judiciais
            acoes = restrictions.filtered(lambda r: r.type == "acao_judicial")
            record.total_acoes = len(acoes)
            record.total_acoes_value = sum(acoes.mapped("value"))
            # Cheques
            cheques = restrictions.filtered(
                lambda r: r.type
                in ("cheque_sem_fundo", "cheque_sustado", "cheque_devolvido")
            )
            record.total_cheques = len(cheques)
            # Falencia
            falencia = restrictions.filtered(
                lambda r: r.type in ("falencia", "recuperacao_judicial")
            )
            record.has_falencia = bool(falencia)
            # Totals
            record.has_restricoes = bool(restrictions)
            record.total_restricoes_value = sum(restrictions.mapped("value"))

    @api.depends("credit_history_ids", "credit_history_ids.value")
    def _compute_credit_history_totals(self):
        for record in self:
            values = record.credit_history_ids.mapped("value")
            record.total_credito_12m = sum(values)
            record.media_credito_12m = (
                sum(values) / len(values) if values else 0
            )

    @api.depends("commitment_ids", "commitment_ids.value")
    def _compute_commitment_totals(self):
        for record in self:
            record.total_comprometido_12m = sum(
                record.commitment_ids.mapped("value")
            )

    @api.constrains("score")
    def _check_score(self):
        for record in self:
            if record.score < 0 or record.score > 1000:
                raise ValidationError(
                    _("O score deve estar entre 0 e 1000.")
                )

    @api.onchange("cnpj_input")
    def _onchange_cnpj_input(self):
        if self.cnpj_input:
            cnpj_clean = re.sub(r"\D", "", self.cnpj_input)
            if len(cnpj_clean) == 14:
                # Format CNPJ
                cnpj_formatted = (
                    f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}."
                    f"{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
                )
                # Search for existing company
                company = self.env["credit.company"].search(
                    ["|", ("cnpj", "=", cnpj_clean), ("cnpj", "=", cnpj_formatted)],
                    limit=1,
                )
                if company:
                    self.company_id = company
                else:
                    # Create new company
                    new_company = self.env["credit.company"].create(
                        {
                            "cnpj": cnpj_formatted,
                            "razao_social": _("Nova Empresa - %s") % cnpj_formatted,
                        }
                    )
                    self.company_id = new_company
                self.cnpj_input = False

    def action_confirm(self):
        """Confirm the credit analysis."""
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _("Apenas consultas em rascunho podem ser confirmadas.")
                )
            record.write(
                {
                    "state": "done",
                    "date_done": fields.Datetime.now(),
                }
            )

    def action_cancel(self):
        """Cancel the credit analysis."""
        for record in self:
            record.state = "cancelled"

    def action_draft(self):
        """Return the credit analysis to draft state."""
        for record in self:
            if record.state != "cancelled":
                raise UserError(
                    _("Apenas consultas canceladas podem voltar para rascunho.")
                )
            record.state = "draft"

    def action_duplicate(self):
        """Duplicate the credit analysis."""
        self.ensure_one()
        new_analysis = self.copy()
        return {
            "name": _("Consulta Duplicada"),
            "type": "ir.actions.act_window",
            "res_model": "credit.analysis",
            "view_mode": "form",
            "res_id": new_analysis.id,
        }

    def action_print_report(self):
        """Print the credit analysis PDF report."""
        self.ensure_one()
        return self.env.ref(
            "credit_analysis.action_report_credit_analysis"
        ).report_action(self)
