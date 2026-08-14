# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

TIPO_REP = [
    ("rep_c", "REP-C (convencional, art. 76)"),
    ("rep_a", "REP-A (alternativo, art. 77)"),
    ("rep_p", "REP-P (via programa, art. 78)"),
]


class L10nBrHrRep(models.Model):
    """Registrador Eletrônico de Ponto (REP) - arts. 75 a 78 da Portaria 671.

    Um registro por equipamento (REP-C), por conjunto autorizado (REP-A) ou por
    programa (REP-P). O REP é a fonte do NSR: a Portaria exige numeração
    sequencial, sem lacunas, iniciando em 1, por estabelecimento (CNPJ/CPF).
    """

    _name = "l10n_br.hr.rep"
    _description = "Registrador Eletrônico de Ponto"
    _order = "company_id, name"

    name = fields.Char(
        required=True,
        help="Identificação interna do registrador.",
    )
    tipo = fields.Selection(
        selection=TIPO_REP,
        required=True,
        default="rep_c",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    tipo_inscricao = fields.Selection(
        selection=[("1", "CNPJ"), ("2", "CPF")],
        string="Tipo de inscrição do empregador",
        default="1",
        required=True,
    )
    cnpj_cpf = fields.Char(
        string="CNPJ/CPF do estabelecimento",
        required=True,
        help="Inscrição do estabelecimento ao qual o REP está vinculado. "
        "O NSR é sequencial por estabelecimento (Anexo V).",
    )
    caepf_cno = fields.Char(
        string="CAEPF/CNO",
        help="Cadastro de Atividade Econômica da Pessoa Física ou Cadastro "
        "Nacional de Obras, quando existir.",
    )
    numero_fabricacao = fields.Char(
        string="Número de fabricação",
        size=17,
        help="Número de fabricação do equipamento (REP-C).",
    )
    numero_inpi = fields.Char(
        string="Registro no INPI",
        size=17,
        help="Número de registro do programa no INPI (REP-P).",
    )
    numero_acordo = fields.Char(
        string="Número do acordo coletivo",
        size=17,
        help="Número do processo do último acordo ou convenção coletiva "
        "depositado (REP-A). Sem acordo depositado, o AFD é gerado com "
        "'99999999999999999'.",
    )
    modelo = fields.Char(
        size=30,
        help="Modelo do equipamento (REP-C).",
    )
    certificacao_inmetro = fields.Char(
        string="Certificação INMETRO",
        help="Número da certificação/homologação publicada no DOU (REP-C).",
    )
    fabricante_tipo_inscricao = fields.Selection(
        selection=[("1", "CNPJ"), ("2", "CPF")],
        string="Tipo de inscrição do fabricante",
        default="1",
    )
    fabricante_cnpj_cpf = fields.Char(string="CNPJ/CPF do fabricante")
    fabricante_nome = fields.Char(string="Fabricante/desenvolvedor")
    atestado_date_start = fields.Date(
        string="Atestado técnico - início",
        help="Vigência do Atestado Técnico e Termo de Responsabilidade "
        "(art. 89). O empregador só pode usar sistema com atestado válido.",
    )
    atestado_date_end = fields.Date(string="Atestado técnico - fim")
    atestado_valido = fields.Boolean(
        compute="_compute_atestado_valido",
        search="_search_atestado_valido",
        string="Atestado vigente",
        help="Falso quando não há atestado cadastrado ou ele está vencido.",
    )
    nsr_ultimo = fields.Integer(
        string="Último NSR",
        default=0,
        readonly=True,
        copy=False,
        help="Último NSR consumido neste REP. O próximo registro recebe "
        "nsr_ultimo + 1 (a Portaria exige início em 1, sem lacunas).",
    )
    marcacao_ids = fields.One2many(
        comodel_name="l10n_br.hr.marcacao",
        inverse_name="rep_id",
        string="Marcações",
    )
    marcacao_count = fields.Integer(
        string="Nº de marcações", compute="_compute_marcacao_count"
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string="Observações")

    _sql_constraints = [
        (
            "numero_fabricacao_uniq",
            "unique(numero_fabricacao, company_id)",
            "Já existe um REP com este número de fabricação nesta empresa.",
        ),
    ]

    @api.depends("atestado_date_start", "atestado_date_end")
    def _compute_atestado_valido(self):
        hoje = fields.Date.context_today(self)
        for rec in self:
            inicio = rec.atestado_date_start
            fim = rec.atestado_date_end
            rec.atestado_valido = bool(
                inicio and inicio <= hoje and (not fim or fim >= hoje)
            )

    def _search_atestado_valido(self, operator, value):
        """Permite filtrar REPs com atestado vencido (painel de conformidade).

        O campo é calculado a partir de duas datas, então a busca traduz a
        pergunta para um domínio sobre elas em vez de varrer a tabela.
        """
        if operator not in ("=", "!="):
            raise UserError(_("Filtro não suportado para o campo 'Atestado vigente'."))
        hoje = fields.Date.context_today(self)
        vigente = [
            ("atestado_date_start", "!=", False),
            ("atestado_date_start", "<=", hoje),
            "|",
            ("atestado_date_end", "=", False),
            ("atestado_date_end", ">=", hoje),
        ]
        procura_vigente = bool(value) == (operator == "=")
        ids_vigentes = self.with_context(active_test=False).search(vigente).ids
        return [("id", "in" if procura_vigente else "not in", ids_vigentes)]

    def _compute_marcacao_count(self):
        agrupado = self.env["l10n_br.hr.marcacao"].read_group(
            [("rep_id", "in", self.ids)], ["rep_id"], ["rep_id"]
        )
        contagem = {g["rep_id"][0]: g["rep_id_count"] for g in agrupado}
        for rec in self:
            rec.marcacao_count = contagem.get(rec.id, 0)

    @api.constrains("tipo", "numero_fabricacao", "numero_inpi")
    def _check_identificacao(self):
        """Cada tipo de REP tem o seu identificador obrigatório (Anexo V)."""
        for rec in self:
            if rec.tipo == "rep_c" and not rec.numero_fabricacao:
                raise ValidationError(
                    _("REP-C exige o número de fabricação do equipamento.")
                )
            if rec.tipo == "rep_p" and not rec.numero_inpi:
                raise ValidationError(
                    _("REP-P exige o número de registro do programa no INPI.")
                )

    def _identificador_afd(self):
        """Campo 7 do registro tipo 1 do AFD, conforme o tipo do REP."""
        self.ensure_one()
        if self.tipo == "rep_c":
            return self.numero_fabricacao or ""
        if self.tipo == "rep_p":
            return self.numero_inpi or ""
        return self.numero_acordo or "9" * 17

    def _proximo_nsr(self, quantidade=1):
        """Reserva ``quantidade`` NSRs de forma segura entre transações.

        O ``SELECT ... FOR UPDATE`` serializa concorrentes no mesmo REP: dois
        processos gravando marcações ao mesmo tempo nunca recebem a mesma
        faixa, o que garante a sequência sem lacunas nem duplicidade exigida
        pelo Anexo V.

        Returns:
            Lista com os NSRs reservados, em ordem crescente.
        """
        self.ensure_one()
        if quantidade < 1:
            return []
        # O SELECT abaixo vai ao banco direto; sem o flush, uma escrita ainda
        # em cache (importação que acabou de alinhar o contador) seria ignorada
        # e a faixa sairia repetida.
        self.flush_recordset(["nsr_ultimo"])
        self.env.cr.execute(
            "SELECT nsr_ultimo FROM l10n_br_hr_rep WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        (atual,) = self.env.cr.fetchone()
        novo = atual + quantidade
        self.env.cr.execute(
            "UPDATE l10n_br_hr_rep SET nsr_ultimo = %s WHERE id = %s",
            (novo, self.id),
        )
        self.invalidate_recordset(["nsr_ultimo"])
        return list(range(atual + 1, novo + 1))

    def _registrar_nsr_externo(self, nsr):
        """Alinha ``nsr_ultimo`` ao maior NSR já visto (importação de AFD).

        Quando as marcações nascem em um REP-C de terceiro, o NSR vem do
        arquivo. Guardamos o maior valor visto para que uma eventual geração
        própria não reaproveite números.
        """
        self.ensure_one()
        if nsr > self.nsr_ultimo:
            self.sudo().write({"nsr_ultimo": nsr})

    def action_view_marcacoes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Marcações"),
            "res_model": "l10n_br.hr.marcacao",
            "view_mode": "tree,form",
            "domain": [("rep_id", "=", self.id)],
            "context": {"default_rep_id": self.id},
        }

    def _check_atestado_vigente(self):
        """Bloqueia uso de REP sem atestado técnico vigente (art. 89, § 4º)."""
        sem_atestado = self.filtered(lambda r: not r.atestado_valido)
        if sem_atestado:
            raise UserError(
                _(
                    "Os REPs abaixo estão sem Atestado Técnico vigente "
                    "(art. 89, § 4º da Portaria 671/2021):\n%s"
                )
                % "\n".join(sem_atestado.mapped("name"))
            )
