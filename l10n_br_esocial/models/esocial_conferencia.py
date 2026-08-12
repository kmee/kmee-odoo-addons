# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

INDICADOR = [
    ("inss_segurado", "INSS retido do segurado"),
    ("irrf", "IRRF retido"),
    ("remuneracao_bruta", "Remuneração bruta"),
    ("base_cp", "Base de contribuição previdenciária"),
    ("cp_contribuinte", "Contribuição do contribuinte (DCTFWeb)"),
]

# Indicadores com contrapartida na folha calculada. Os demais são informativos:
# o governo devolve, a folha ainda não calcula (encargos patronais, RF-31).
INDICADORES_COMPARATIVOS = ("inss_segurado", "irrf")


class ESocialConferencia(models.Model):
    """Conferência da competência: folha calculada x totalizador devolvido.

    A folha é a verdade interna; o totalizador é a verdade oficial que virou
    DCTFWeb. Divergência entre as duas é erro de fechamento, e este modelo
    existe para que ela apareça antes de o prazo vencer, não depois.
    """

    _name = "l10n_br.esocial.conferencia"
    _description = "eSocial - Conferência da Competência"
    _order = "per_apur desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        required=True,
        help="AAAA-MM para a folha mensal, AAAA para o 13º salário.",
    )
    ind_apuracao = fields.Selection(
        [
            ("1", "Mensal"),
            ("2", "Anual (13º Salário)"),
        ],
        string="Tipo Apuração",
        default="1",
        required=True,
    )
    tolerancia = fields.Monetary(
        string="Tolerância",
        default=0.01,
        currency_field="currency_id",
        help="Diferença absoluta aceita por indicador antes de virar "
        "divergência (arredondamento de centavos).",
    )
    state = fields.Selection(
        [
            ("draft", "Não apurada"),
            ("ok", "Conferida"),
            ("divergente", "Divergente"),
        ],
        string="Situação",
        compute="_compute_state",
        store=True,
    )
    data_apuracao = fields.Datetime(string="Apurada em", readonly=True)
    linha_ids = fields.One2many(
        "l10n_br.esocial.conferencia.linha",
        "conferencia_id",
        string="Indicadores",
    )
    divergencia_count = fields.Integer(compute="_compute_state", store=True)
    totalizador_ids = fields.Many2many(
        "l10n_br.esocial.totalizador",
        string="Totalizadores",
        compute="_compute_apoio",
    )
    payslip_ids = fields.Many2many(
        "hr.payslip",
        string="Holerites",
        compute="_compute_apoio",
    )
    payslip_sem_evento_ids = fields.Many2many(
        "hr.payslip",
        string="Holerites sem S-1200",
        compute="_compute_apoio",
        help="Holerites confirmados da competência que não foram enviados ao "
        "eSocial. São a causa mais comum de divergência no fechamento.",
    )
    payslip_sem_evento_count = fields.Integer(compute="_compute_apoio")

    _sql_constraints = [
        (
            "competencia_uniq",
            "unique(company_id, per_apur, ind_apuracao)",
            "Já existe uma conferência para esta competência.",
        ),
    ]

    @api.depends("per_apur", "ind_apuracao")
    def _compute_name(self):
        for rec in self:
            rec.name = _("Conferência %(per)s") % {"per": rec.per_apur or ""}

    @api.depends("linha_ids.divergente", "data_apuracao")
    def _compute_state(self):
        for rec in self:
            divergentes = rec.linha_ids.filtered("divergente")
            rec.divergencia_count = len(divergentes)
            if not rec.data_apuracao:
                rec.state = "draft"
            else:
                rec.state = "divergente" if divergentes else "ok"

    @api.depends("per_apur", "ind_apuracao", "company_id")
    def _compute_apoio(self):
        for rec in self:
            rec.totalizador_ids = rec._buscar_totalizadores()
            payslips = rec._buscar_payslips()
            rec.payslip_ids = payslips
            sem_evento = payslips.filtered(
                lambda slip: not slip.l10n_br_esocial_s1200_id.evento_id
                or slip.l10n_br_esocial_s1200_id.evento_id.state != "success"
            )
            rec.payslip_sem_evento_ids = sem_evento
            rec.payslip_sem_evento_count = len(sem_evento)

    # ── Fontes de dado ─────────────────────────────────────────────────────

    def _buscar_totalizadores(self):
        self.ensure_one()
        if not self.per_apur:
            return self.env["l10n_br.esocial.totalizador"]
        return self.env["l10n_br.esocial.totalizador"].search(
            self._dominio_totalizador()
        )

    def _dominio_totalizador(self, tipo=None):
        self.ensure_one()
        dominio = [
            ("company_id", "=", self.company_id.id),
            ("per_apur", "=", self.per_apur),
        ]
        if tipo:
            dominio.append(("tipo", "=", tipo))
        return dominio

    def _buscar_payslips(self):
        """Holerites confirmados da competência (fonte da folha calculada)."""
        self.ensure_one()
        if not self.per_apur:
            return self.env["hr.payslip"]
        if self.ind_apuracao == "2" and "-" not in self.per_apur:
            inicio = f"{self.per_apur}-01-01"
            fim = f"{self.per_apur}-12-31"
        else:
            ano, mes = self.per_apur.split("-")
            inicio = f"{ano}-{mes}-01"
            ultimo_dia = fields.Date.end_of(fields.Date.to_date(inicio), "month")
            fim = fields.Date.to_string(ultimo_dia)
        return self.env["hr.payslip"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "done"),
                ("date_from", ">=", inicio),
                ("date_from", "<=", fim),
            ]
        )

    def _total_folha_por_codigo(self, codigos):
        """Soma o valor absoluto das linhas de holerite com esses códigos."""
        self.ensure_one()
        linhas = (
            self._buscar_payslips()
            .mapped("line_ids")
            .filtered(lambda linha: linha.code in codigos)
        )
        return sum(abs(linha.total) for linha in linhas)

    def _total_totalizador(self, tipo, grupo, descricao=None, apenas_consolidado=False):
        """Soma de um grupo de linhas dos totalizadores da competência."""
        self.ensure_one()
        totalizadores = self.env["l10n_br.esocial.totalizador"].search(
            self._dominio_totalizador(tipo)
        )
        if not totalizadores:
            return None
        dominio = [
            ("totalizador_id", "in", totalizadores.ids),
            ("grupo", "=", grupo),
        ]
        if descricao is not None:
            dominio.append(("descricao", "=", descricao))
        if apenas_consolidado:
            # O S-5002 traz o consolidado do beneficiário e o detalhe por
            # demonstrativo; somar os dois contaria o IRRF duas vezes.
            dominio.append(("per_ref", "=", False))
        linhas = self.env["l10n_br.esocial.totalizador.linha"].search(dominio)
        return sum(linhas.mapped("valor"))

    # ── Apuração ───────────────────────────────────────────────────────────

    def _valores_inss_segurado(self):
        """INSS retido: S-5011 consolidado, com S-5001 como alternativa."""
        self.ensure_one()
        valor = self._total_totalizador("S-5011", "cp_seg", descricao="vrDescCP")
        fonte = "S-5011 infoCPSeg/vrDescCP"
        if valor is None:
            valor = self._total_totalizador(
                "S-5001", "info_cp_calc", descricao="vrDescSeg"
            )
            fonte = "S-5001 infoCpCalc/vrDescSeg"
        return valor, fonte, self._total_folha_por_codigo(("INSS",)), "Rubrica INSS"

    def _valores_irrf(self):
        """IRRF retido: S-5012 consolidado, com S-5002 como alternativa."""
        self.ensure_one()
        valor = self._total_totalizador("S-5012", "cr_men", descricao="vrCRMen")
        fonte = "S-5012 infoCRMen/vrCRMen"
        if valor is None:
            valor = self._total_totalizador(
                "S-5002", "cr_men", descricao="vlrCRMen", apenas_consolidado=True
            )
            fonte = "S-5002 consolidApurMen/vlrCRMen"
        return valor, fonte, self._total_folha_por_codigo(("IRRF",)), "Rubrica IRRF"

    def _linhas_apuracao(self):
        """Valores de cada indicador: (folha, totalizador, fontes)."""
        self.ensure_one()
        (
            inss_tot,
            inss_fonte,
            inss_folha,
            inss_folha_fonte,
        ) = self._valores_inss_segurado()
        irrf_tot, irrf_fonte, irrf_folha, irrf_folha_fonte = self._valores_irrf()
        base_cp = self._total_totalizador("S-5011", "base_cp", descricao="vrBcCp00")
        cp_contrib = self._total_totalizador("S-5011", "cr_contrib", descricao="vrCR")
        return [
            {
                "indicador": "inss_segurado",
                "valor_folha": inss_folha,
                "valor_totalizador": inss_tot or 0.0,
                "sem_totalizador": inss_tot is None,
                "fonte_folha": inss_folha_fonte,
                "fonte_totalizador": inss_fonte,
            },
            {
                "indicador": "irrf",
                "valor_folha": irrf_folha,
                "valor_totalizador": irrf_tot or 0.0,
                "sem_totalizador": irrf_tot is None,
                "fonte_folha": irrf_folha_fonte,
                "fonte_totalizador": irrf_fonte,
            },
            {
                "indicador": "remuneracao_bruta",
                "valor_folha": self._total_folha_por_codigo(("GROSS",)),
                "valor_totalizador": 0.0,
                "sem_totalizador": True,
                "fonte_folha": "Rubrica GROSS",
                "fonte_totalizador": _("sem contrapartida direta no totalizador"),
            },
            {
                "indicador": "base_cp",
                "valor_folha": 0.0,
                "valor_totalizador": base_cp or 0.0,
                "sem_totalizador": base_cp is None,
                "fonte_folha": _("não calculada pela folha"),
                "fonte_totalizador": "S-5011 basesCp/vrBcCp00",
            },
            {
                "indicador": "cp_contribuinte",
                "valor_folha": 0.0,
                "valor_totalizador": cp_contrib or 0.0,
                "sem_totalizador": cp_contrib is None,
                "fonte_folha": _("encargos patronais ainda não calculados (RF-31)"),
                "fonte_totalizador": "S-5011 infoCRContrib/vrCR",
            },
        ]

    def action_apurar(self):
        """Recalcula os indicadores da competência a partir das duas fontes."""
        for rec in self:
            if not rec.per_apur:
                raise UserError(_("Informe o período de apuração."))
            rec.linha_ids.unlink()
            rec.linha_ids = [(0, 0, vals) for vals in rec._linhas_apuracao()]
            rec.data_apuracao = fields.Datetime.now()
        return True

    @api.model
    def obter_ou_criar(self, company, per_apur, ind_apuracao="1"):
        """Conferência da competência, criada na primeira necessidade."""
        conferencia = self.search(
            [
                ("company_id", "=", company.id),
                ("per_apur", "=", per_apur),
                ("ind_apuracao", "=", ind_apuracao),
            ],
            limit=1,
        )
        if conferencia:
            return conferencia
        return self.create(
            {
                "company_id": company.id,
                "per_apur": per_apur,
                "ind_apuracao": ind_apuracao,
            }
        )

    def action_ver_holerites_sem_evento(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Holerites sem S-1200 aceito"),
            "res_model": "hr.payslip",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.payslip_sem_evento_ids.ids)],
        }


class ESocialConferenciaLinha(models.Model):
    _name = "l10n_br.esocial.conferencia.linha"
    _description = "eSocial - Indicador de Conferência"
    _order = "conferencia_id, indicador"

    conferencia_id = fields.Many2one(
        "l10n_br.esocial.conferencia",
        string="Conferência",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="conferencia_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="conferencia_id.currency_id",
        readonly=True,
    )
    per_apur = fields.Char(
        related="conferencia_id.per_apur",
        store=True,
        readonly=True,
    )
    indicador = fields.Selection(
        INDICADOR,
        required=True,
    )
    comparativo = fields.Boolean(
        compute="_compute_comparativo",
        store=True,
        help="Falso nos indicadores que só existem do lado do governo — eles "
        "são informativos e nunca acusam divergência.",
    )
    sem_totalizador = fields.Boolean(
        help="Nenhum totalizador da competência informou este indicador.",
    )
    valor_folha = fields.Monetary(
        string="Folha Calculada",
        currency_field="currency_id",
    )
    valor_totalizador = fields.Monetary(
        string="Totalizador eSocial",
        currency_field="currency_id",
    )
    diferenca = fields.Monetary(
        string="Diferença",
        compute="_compute_diferenca",
        store=True,
        currency_field="currency_id",
    )
    divergente = fields.Boolean(
        compute="_compute_diferenca",
        store=True,
    )
    fonte_folha = fields.Char(string="Fonte (Folha)")
    fonte_totalizador = fields.Char(string="Fonte (Totalizador)")

    @api.depends("indicador")
    def _compute_comparativo(self):
        for rec in self:
            rec.comparativo = rec.indicador in INDICADORES_COMPARATIVOS

    @api.depends(
        "valor_folha",
        "valor_totalizador",
        "comparativo",
        "sem_totalizador",
        "conferencia_id.tolerancia",
    )
    def _compute_diferenca(self):
        for rec in self:
            rec.diferenca = rec.valor_folha - rec.valor_totalizador
            tolerancia = rec.conferencia_id.tolerancia or 0.0
            if not rec.comparativo:
                rec.divergente = False
            elif rec.sem_totalizador:
                # Folha com valor e governo sem devolver nada é divergência:
                # sinal de evento não transmitido ou não processado.
                rec.divergente = bool(rec.valor_folha)
            else:
                rec.divergente = abs(rec.diferenca) > tolerancia
