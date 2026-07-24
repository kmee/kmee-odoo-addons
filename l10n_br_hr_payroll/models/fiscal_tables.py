# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tabelas fiscais da folha de pagamento parametrizadas por vigência.

Substituem as constantes hardcoded (INSS/IRRF/salário família/salário mínimo)
que só contemplavam 2024. Cada tabela guarda ``date_start``/``date_end`` e o
resolvedor devolve a vigente na competência do holerite, levantando
``UserError`` quando não há tabela cadastrada (nunca cai silenciosamente em
2024).

Os valores são carregados de ``data/*.csv`` e têm como fonte as tabelas de
referência do eSocial (``l10n_br_esocial``). Este módulo NÃO depende do
eSocial: a dependência real é a inversa.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date

from . import salary_rules_br


class L10nBrPayrollTabelaMixin(models.AbstractModel):
    """Vigência (date_start/date_end) + resolvedor da tabela vigente."""

    _name = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Tabela Fiscal da Folha por Vigência"
    _order = "date_start desc"

    # Rótulo usado na mensagem de erro (sobrescrito nos modelos concretos).
    _tabela_label = "tabela fiscal"

    date_start = fields.Date(
        string="Início da Vigência",
        required=True,
        index=True,
    )
    date_end = fields.Date(
        string="Fim da Vigência",
        index=True,
        help="Vazio = vigente por prazo indeterminado.",
    )
    active = fields.Boolean(default=True)

    @api.model
    def _vigentes(self, competencia, order=None):
        """Registros vigentes na ``competencia`` (date).

        Levanta ``UserError`` se não houver nenhum — a folha NUNCA deve cair
        silenciosamente em uma tabela de outro ano.
        """
        if not competencia:
            raise UserError(
                _(
                    "Não é possível resolver a %s: o holerite está sem "
                    "competência (date_from/date_to)."
                )
                % self._tabela_label
            )
        recs = self.search(
            [
                ("date_start", "<=", competencia),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", competencia),
            ],
            order=order,
        )
        if not recs:
            raise UserError(
                _(
                    "Não há %(label)s vigente para a competência %(data)s. "
                    "Cadastre a vigência em Folha de Pagamento › Configuração "
                    "› Tabelas Fiscais."
                )
                % {
                    "label": self._tabela_label,
                    "data": format_date(self.env, competencia),
                }
            )
        return recs


class L10nBrPayrollInssFaixa(models.Model):
    _name = "l10n_br.hr.payroll.inss.faixa"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Faixa de Contribuição INSS por Vigência"
    _order = "date_start desc, valor_max"
    _tabela_label = "tabela de INSS"

    name = fields.Char(compute="_compute_name", store=True)
    valor_min = fields.Float(string="Salário de Contribuição (De)", digits=(16, 2))
    valor_max = fields.Float(string="Salário de Contribuição (Até)", digits=(16, 2))
    aliquota = fields.Float(string="Alíquota (%)", digits=(5, 2))
    parcela_deduzir = fields.Float(
        string="Parcela a Deduzir",
        digits=(16, 6),
        help="Parcela a deduzir do método simplificado (referência). O "
        "cálculo usa a incidência progressiva por faixa.",
    )

    @api.depends("valor_min", "valor_max", "aliquota", "date_start")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] R$ %.2f–%.2f · %.2f%%" % (
                rec.date_start or "",
                rec.valor_min,
                rec.valor_max,
                rec.aliquota,
            )

    @api.model
    def _tabela(self, competencia):
        """Faixas progressivas vigentes como ``[(teto, aliquota_fracao), ...]``
        ordenadas por teto ascendente."""
        faixas = self._vigentes(competencia, order="valor_max asc")
        return [(f.valor_max, f.aliquota / 100.0) for f in faixas]

    @api.model
    def _teto(self, competencia):
        """(teto_salario, valor_maximo_contribuicao) da competência."""
        tabela = self._tabela(competencia)
        teto_salario = max(t[0] for t in tabela)
        return teto_salario, salary_rules_br.calc_inss(teto_salario, tabela)

    @api.model
    def _salario_minimo(self, competencia):
        """Salário mínimo da competência.

        Derivado do teto da 1ª faixa do INSS, que por definição legal da
        tabela progressiva coincide com o salário mínimo nacional. Evita
        cadastrar valores fora dos CSVs de origem.
        """
        return min(t[0] for t in self._tabela(competencia))


class L10nBrPayrollIrrfFaixa(models.Model):
    _name = "l10n_br.hr.payroll.irrf.faixa"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Faixa de Retenção IRRF por Vigência"
    _order = "date_start desc, base_max"
    _tabela_label = "tabela de IRRF"

    name = fields.Char(compute="_compute_name", store=True)
    base_min = fields.Float(string="Base de Cálculo (De)", digits=(16, 2))
    base_max = fields.Float(string="Base de Cálculo (Até)", digits=(16, 2))
    aliquota = fields.Float(string="Alíquota (%)", digits=(5, 2))
    parcela_deduzir = fields.Float(string="Parcela a Deduzir", digits=(16, 2))

    @api.depends("base_min", "base_max", "aliquota", "date_start")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] R$ %.2f–%.2f · %.2f%%" % (
                rec.date_start or "",
                rec.base_min,
                rec.base_max,
                rec.aliquota,
            )

    @api.model
    def _tabela(self, competencia):
        """Faixas vigentes como ``[(base_max, aliquota_fracao, parcela), ...]``
        ordenadas por base ascendente."""
        faixas = self._vigentes(competencia, order="base_max asc")
        return [(f.base_max, f.aliquota / 100.0, f.parcela_deduzir) for f in faixas]


class L10nBrPayrollSalFamiliaFaixa(models.Model):
    _name = "l10n_br.hr.payroll.sal.familia.faixa"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Faixa de Salário Família por Vigência"
    _order = "date_start desc, base_max"
    _tabela_label = "tabela de salário família"

    name = fields.Char(compute="_compute_name", store=True)
    base_max = fields.Float(
        string="Remuneração (Até)",
        digits=(16, 2),
        help="Limite de remuneração para ter direito à cota.",
    )
    valor = fields.Float(string="Valor da Cota", digits=(16, 2))

    @api.depends("base_max", "valor", "date_start")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] até R$ %.2f → R$ %.2f" % (
                rec.date_start or "",
                rec.base_max,
                rec.valor,
            )

    @api.model
    def _tabela(self, competencia):
        """Faixas vigentes como ``[(base_max, valor), ...]`` ascendente."""
        faixas = self._vigentes(competencia, order="base_max asc")
        return [(f.base_max, f.valor) for f in faixas]


class L10nBrPayrollIrrfDependente(models.Model):
    _name = "l10n_br.hr.payroll.irrf.dependente"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Dedução por Dependente do IRRF por Vigência"
    _order = "date_start desc"
    _tabela_label = "dedução por dependente do IRRF"

    name = fields.Char(compute="_compute_name", store=True)
    valor = fields.Float(string="Dedução por Dependente", digits=(16, 2))

    @api.depends("valor", "date_start")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] R$ %.2f" % (rec.date_start or "", rec.valor)

    @api.model
    def _valor(self, competencia):
        """Valor da dedução por dependente vigente na competência."""
        return self._vigentes(competencia, order="date_start desc")[0].valor
