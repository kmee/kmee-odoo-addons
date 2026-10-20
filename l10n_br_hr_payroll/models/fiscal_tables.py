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
    def _vigentes_opcional(self, competencia, order=None):
        """Como ``_vigentes``, mas devolve recordset VAZIO se não houver tabela.

        Para tabelas que só passam a existir a partir de certa competência e
        cuja ausência é o comportamento legal correto (ex.: o redutor do IRPF
        da Lei 15.270/2025, inexistente antes de 01/2026). Continua exigindo a
        competência.
        """
        if not competencia:
            raise UserError(
                _(
                    "Não é possível resolver a %s: o holerite está sem "
                    "competência (date_from/date_to)."
                )
                % self._tabela_label
            )
        return self.search(
            [
                ("date_start", "<=", competencia),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", competencia),
            ],
            order=order,
        )

    @api.model
    def _vigentes(self, competencia, order=None):
        """Registros vigentes na ``competencia`` (date).

        Levanta ``UserError`` se não houver nenhum - a folha NUNCA deve cair
        silenciosamente em uma tabela de outro ano.
        """
        recs = self._vigentes_opcional(competencia, order=order)
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
            rec.name = "[%s] R$ %.2f-%.2f · %.2f%%" % (
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
            rec.name = "[%s] R$ %.2f-%.2f · %.2f%%" % (
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

    # Fator legal do desconto simplificado mensal (Lei 9.250/95, art. 4º, § 2º,
    # incluído pela Lei 14.663/2023, art. 6º): a parcela corresponde a 25% do
    # valor máximo da faixa de isenção da tabela mensal vigente.
    FATOR_DESCONTO_SIMPLIFICADO = 0.25

    @api.model
    def _desconto_simplificado(self, competencia):
        """Parcela do desconto simplificado mensal do IRRF por competência.

        Vigente desde 05/2023 (Lei 9.250/95, art. 4º, § 2º, incluído pela Lei
        14.663/2023, art. 6º): opcionalmente, no lugar das deduções legais
        (INSS, dependentes, pensão), o contribuinte pode abater uma parcela
        fixa correspondente a **25% do teto da faixa de isenção** da tabela
        mensal vigente. A retenção deve usar a forma mais favorável (menor
        imposto), ver a regra salarial IRRF.

        A opção existe em CADA apuração, porque a IN RFB 2.141/2023 inseriu o
        dispositivo em cada base da IN RFB 1.500/2014: art. 13, § 8º (13º
        salário), art. 29, § 5º (férias) e art. 52, § 3º (rendimentos do
        trabalho em geral, folha mensal).

        Deriva o valor da própria tabela de IRRF já parametrizada por
        vigência (não introduz constante nova): teto da faixa de isenção é o
        menor ``base_max`` da tabela (faixa com alíquota zero).

        Conferência com os valores oficiais:
          - 05/2023-01/2024: 25% x 2.112,00 = 528,00
          - 02/2024-04/2025: 25% x 2.259,20 = 564,80
          - a partir 05/2025: 25% x 2.428,80 = 607,20

        Pendência (documentada): o fator de 25% é fixado em lei; caso uma
        vigência futura altere o percentual, basta sobrepor este método ou
        adicionar um campo de fator por vigência.
        """
        tabela = self._tabela(competencia)
        teto_isencao = min(base_max for base_max, _aliq, _parcela in tabela)
        return salary_rules_br.round_money(
            self.FATOR_DESCONTO_SIMPLIFICADO * teto_isencao
        )


class L10nBrPayrollIrrfRedutor(models.Model):
    _name = "l10n_br.hr.payroll.irrf.redutor"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Faixa do Redutor do IRPF na Fonte por Vigência"
    _order = "date_start desc, rendimento_max"
    _tabela_label = "tabela do redutor do IRPF"

    name = fields.Char(compute="_compute_name", store=True)
    rendimento_max = fields.Float(
        string="Rendimento Bruto (Até)",
        digits=(16, 2),
        help="Teto do rendimento tributável BRUTO do mês para a faixa. Acima "
        "do maior teto cadastrado não há redutor (corte seco).",
    )
    valor_fixo = fields.Float(
        string="Parcela Fixa",
        digits=(16, 2),
        help="Parcela fixa da fórmula do redutor.",
    )
    fator = fields.Float(
        string="Fator sobre o Rendimento",
        digits=(16, 6),
        help="Coeficiente multiplicado pelo rendimento bruto do mês. "
        "Redutor = Parcela Fixa - Fator x rendimento bruto. Zero = redutor "
        "fixo (isenção integral até o teto da faixa).",
    )

    @api.depends("rendimento_max", "valor_fixo", "fator", "date_start")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] até R$ %.2f -> %.2f - %.6f x rendimento" % (
                rec.date_start or "",
                rec.rendimento_max,
                rec.valor_fixo,
                rec.fator,
            )

    @api.model
    def _tabela(self, competencia):
        """Faixas do redutor vigentes como ``[(teto, valor_fixo, fator), ...]``
        ascendente.

        Devolve lista VAZIA quando a competência não tem redutor (qualquer
        competência anterior a 01/2026, antes da Lei 15.270/2025) - nesse caso
        o comportamento anterior da folha é integralmente preservado.
        """
        faixas = self._vigentes_opcional(competencia, order="rendimento_max asc")
        return [(f.rendimento_max, f.valor_fixo, f.fator) for f in faixas]


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
            rec.name = "[%s] até R$ %.2f -> R$ %.2f" % (
                rec.date_start or "",
                rec.base_max,
                rec.valor,
            )

    @api.model
    def _tabela(self, competencia):
        """Faixas vigentes como ``[(base_max, valor), ...]`` ascendente."""
        faixas = self._vigentes(competencia, order="base_max asc")
        return [(f.base_max, f.valor) for f in faixas]


class L10nBrPayrollCprbTransicao(models.Model):
    """Transição da reoneração da folha (CPRB) por vigência anual.

    Empresas dos setores dos arts. 7º e 8º da Lei 12.546/2011 podem optar por
    substituir a contribuição patronal sobre a folha (CPP, art. 22, I e III da
    Lei 8.212/91) pela CPRB, calculada sobre a receita bruta. A Lei
    14.973/2024 (arts. 9º-A e 9º-B da Lei 12.546/2011) acabou com a
    substituição integral: de 2025 a 2027 vale um regime híbrido em que uma
    PROPORÇÃO crescente da CPP volta a incidir sobre a folha, até a extinção
    do regime em 2028.

    Cada linha guarda a proporção do ano, não a alíquota efetiva:

      - ``perc_cprb``: proporção da CPRB (sobre a receita) mantida no ano -
        registrada aqui para conciliar com o R-2060 da EFD-Reinf, que é
        apurado pelo próprio contribuinte;
      - ``perc_cpp``: proporção dos 20% da CPP devida sobre a folha;
      - ``perc_cpp_13``: idem para o 13º salário, que tem cronograma PRÓPRIO
        - o art. 9º-A, §1º afasta os incisos I e III do art. 22 sobre a
        gratificação natalina de 2025 a 2027 (coluna separada exatamente por
        isso, e não por simetria). A dispensa é só desses incisos: RAT e
        terceiros continuam integrais sobre o 13º.

    Fora desta tabela, porque são dados de competência/cadastro e não de
    vigência legal: a opção pela CPRB e o ``percRedContrib`` da atividade
    concomitante, ambos em ``res.company``.

    Não há linha aberta antes de 2024: o resolvedor levanta ``UserError`` em
    vez de cair na proporção de outro ano (mesma disciplina das demais
    tabelas fiscais deste módulo).
    """

    _name = "l10n_br.hr.payroll.cprb.transicao"
    _inherit = "l10n_br.hr.payroll.tabela.mixin"
    _description = "Transição da Reoneração da Folha (CPRB) por Vigência"
    _order = "date_start desc"
    _tabela_label = "tabela de transição da CPRB"

    name = fields.Char(compute="_compute_name", store=True)
    perc_cprb = fields.Float(
        string="Proporção da CPRB (%)",
        digits=(5, 2),
        help="Proporção da contribuição sobre a receita bruta mantida no "
        "ano (100 = substituição total, como até 2024).",
    )
    perc_cpp = fields.Float(
        string="Proporção da CPP sobre a Folha (%)",
        digits=(5, 2),
        help="Proporção dos 20% do art. 22, I da Lei 8.212/91 devida sobre a "
        "folha no ano. Em 2026: 50 (alíquota efetiva de 10%).",
    )
    perc_cpp_13 = fields.Float(
        string="Proporção da CPP sobre o 13º (%)",
        digits=(5, 2),
        help="Proporção da CPP devida sobre a gratificação natalina. Zero de "
        "2025 a 2027 (Lei 12.546/2011, art. 9º-A, §1º).",
    )
    base_legal = fields.Char(
        help="Dispositivo que fixa a proporção do ano, para auditoria da folha."
    )

    @api.depends("date_start", "perc_cprb", "perc_cpp")
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] CPRB %.0f%% · CPP folha %.0f%%" % (
                rec.date_start or "",
                rec.perc_cprb,
                rec.perc_cpp,
            )

    @api.model
    def _proporcao_cpp(self, competencia, decimo_terceiro=False):
        """Proporção da CPP devida sobre a folha na ``competencia`` (0 a 100).

        Args:
            competencia: Data do fato gerador (competência do holerite).
            decimo_terceiro: ``True`` para a apuração do 13º salário, que tem
                cronograma próprio (``perc_cpp_13``).

        Returns:
            Proporção em pontos percentuais.
        """
        linha = self._vigentes(competencia, order="date_start desc")[0]
        return linha.perc_cpp_13 if decimo_terceiro else linha.perc_cpp


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
