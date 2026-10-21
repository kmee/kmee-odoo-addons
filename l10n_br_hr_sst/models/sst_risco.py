# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .sst_dominios import (
    COD_AGENTE_NOCIVO_AUSENCIA,
    GRAU_INSALUBRIDADE,
    SIM_NAO,
    TIPO_AVALIACAO,
    UNIDADE_MEDIDA,
    UTILIZACAO_EPC,
    UTILIZACAO_EPI,
)


class L10nBrSstRisco(models.Model):
    """Fator de risco de um ambiente (grupo agNoc do S-2240).

    Um risco vale para o ambiente inteiro ou, quando ``job_ids`` está
    preenchido, apenas para as funções listadas. É a partir daqui que se deriva
    o S-2240, o adicional de insalubridade/periculosidade e o adicional de
    GILRAT da aposentadoria especial.
    """

    _name = "l10n_br.sst.risco"
    _description = "SST - Fator de Risco"
    _inherit = ["mail.thread"]
    _order = "ambiente_id, agente_nocivo_id"

    name = fields.Char(
        string="Risco",
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        related="ambiente_id.company_id",
        store=True,
        readonly=True,
    )
    ambiente_id = fields.Many2one(
        "l10n_br.sst.ambiente",
        string="Ambiente",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    laudo_id = fields.Many2one(
        "l10n_br.sst.laudo",
        string="Laudo",
        tracking=True,
        help="Laudo que documenta este risco. Sem laudo, o risco não sustenta "
        "adicional na folha nem informação no S-2240.",
    )
    job_ids = fields.Many2many(
        "hr.job",
        relation="l10n_br_sst_risco_hr_job_rel",
        column1="risco_id",
        column2="job_id",
        string="Funções Expostas",
        help="Vazio significa que o risco atinge todas as funções do ambiente.",
    )
    agente_nocivo_id = fields.Many2one(
        "l10n_br.esocial.agente.nocivo",
        string="Agente Nocivo",
        required=True,
        tracking=True,
        help="Tabela 24 do eSocial (agentes nocivos e atividades, "
        "aposentadoria especial). Ausência de exposição é o código "
        "09.01.001, e não a falta de registro.",
    )
    cod_ag_noc = fields.Char(
        related="agente_nocivo_id.codigo",
        string="Código do Agente Nocivo",
        store=True,
    )
    ausencia_de_risco = fields.Boolean(
        string="Ausência de Agente Nocivo",
        compute="_compute_ausencia_de_risco",
        store=True,
    )
    descricao = fields.Text(
        string="Descrição Complementar",
        help="Preenche dscAgNoc quando o agente exige detalhamento.",
    )
    # ── Avaliação quantitativa (NR-9) ──────────────────────────────────────
    tp_aval = fields.Selection(
        TIPO_AVALIACAO,
        string="Tipo de Avaliação",
        tracking=True,
    )
    intensidade = fields.Float(
        string="Intensidade / Concentração",
        digits=(11, 4),
    )
    limite_tolerancia = fields.Float(
        string="Limite de Tolerância",
        digits=(11, 4),
    )
    un_med = fields.Selection(
        UNIDADE_MEDIDA,
        string="Unidade de Medida",
    )
    tecnica_medicao = fields.Char(
        string="Técnica de Medição",
    )
    nr_proc_jud = fields.Char(
        string="Processo Judicial",
        help="Número do processo judicial que afasta a exposição, quando houver.",
    )
    # ── Proteção coletiva e individual (grupo epcEpi) ──────────────────────
    utiliz_epc = fields.Selection(
        UTILIZACAO_EPC,
        string="Utilização de EPC",
        default="0",
    )
    efic_epc = fields.Selection(
        SIM_NAO,
        string="EPC Eficaz",
    )
    utiliz_epi = fields.Selection(
        UTILIZACAO_EPI,
        string="Utilização de EPI",
        default="0",
    )
    efic_epi = fields.Selection(
        SIM_NAO,
        string="EPI Eficaz",
    )
    # ── Consequências previdenciárias e trabalhistas ───────────────────────
    aposentadoria_especial_id = fields.Many2one(
        "l10n_br.esocial.aposentadoria.especial",
        string="Enquadramento (Anexo IV do Decreto 3.048/1999)",
        help="Classificação do agente nocivo no Anexo IV do Decreto "
        "3.048/1999, para fins de aposentadoria especial. Não é tabela do "
        "eSocial: no S-2240 o agente vai pelo código da Tabela 24.",
    )
    financiamento_aposent_id = fields.Many2one(
        "l10n_br.esocial.financiamento.aposent",
        string="Financiamento da Aposentadoria Especial",
        help="Tabela 02 do eSocial: define o adicional de GILRAT (12%, 9% ou "
        "6%) devido pela exposição.",
    )
    insalubridade = fields.Boolean(
        string="Gera Insalubridade",
        tracking=True,
    )
    grau_insalubridade = fields.Selection(
        GRAU_INSALUBRIDADE,
        string="Grau de Insalubridade",
        tracking=True,
    )
    periculosidade = fields.Boolean(
        string="Gera Periculosidade",
        tracking=True,
    )
    aviso_adicionais = fields.Char(
        string="Aviso sobre os Adicionais",
        compute="_compute_aviso_adicionais",
        help="O mesmo agente pode ser insalubre e perigoso (radiação "
        "ionizante, por exemplo, está no Anexo 5 da NR-15 e na NR-16). O "
        "laudo registra os dois; o que não se acumula é o pagamento.",
    )
    # ── Vigência ───────────────────────────────────────────────────────────
    date_from = fields.Date(
        string="Início da Exposição",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_to = fields.Date(
        string="Fim da Exposição",
        tracking=True,
    )
    active = fields.Boolean(default=True)

    @api.depends("agente_nocivo_id", "ambiente_id")
    def _compute_name(self):
        for rec in self:
            partes = [rec.ambiente_id.name, rec.agente_nocivo_id.name]
            rec.name = " / ".join(parte for parte in partes if parte)

    @api.depends("agente_nocivo_id.codigo")
    def _compute_ausencia_de_risco(self):
        for rec in self:
            rec.ausencia_de_risco = (
                rec.agente_nocivo_id.codigo == COD_AGENTE_NOCIVO_AUSENCIA
            )

    @api.constrains("date_from", "date_to")
    def _check_vigencia(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(
                    _("Risco %(nome)s: o fim da exposição é anterior ao início.")
                    % {"nome": rec.name or rec.agente_nocivo_id.name}
                )

    @api.depends("insalubridade", "periculosidade")
    def _compute_aviso_adicionais(self):
        """Avisa que insalubridade e periculosidade não se pagam juntas.

        O laudo descreve o ambiente e pode apontar os dois (NR-15, item 15.3, e
        NR-16, item 16.2.1). A vedação é do pagamento: CLT, art. 193, par. 2,
        e TST IRR Tema 17 (IRR-239-55.2011.5.02.0319), que valem mesmo quando
        os fatos geradores são distintos. Bloquear o cadastro esconderia do
        laudo uma exposição real; a escolha do adicional é feita no contrato.
        """
        for rec in self:
            rec.aviso_adicionais = (
                _(
                    "Este risco gera insalubridade e periculosidade. Os dois "
                    "adicionais não se acumulam (CLT, art. 193, par. 2, e TST "
                    "IRR Tema 17): o empregado opta por um deles, e sem opção "
                    "a folha paga o de maior valor."
                )
                if rec.insalubridade and rec.periculosidade
                else False
            )

    @api.constrains("insalubridade", "grau_insalubridade")
    def _check_adicionais(self):
        """Insalubridade exige o grau apurado no laudo (NR-15, item 15.2)."""
        for rec in self:
            if rec.insalubridade and not rec.grau_insalubridade:
                raise ValidationError(
                    _(
                        "Risco %(nome)s: informe o grau de insalubridade "
                        "(mínimo, médio ou máximo) apurado no laudo."
                    )
                    % {"nome": rec.name or rec.agente_nocivo_id.name}
                )

    @api.constrains("ausencia_de_risco", "utiliz_epc", "utiliz_epi")
    def _check_ausencia_de_risco(self):
        """Sem agente nocivo, EPC e EPI só podem ser 'não se aplica'.

        Regra de validação do próprio S-2240: informar proteção contra um risco
        declarado inexistente é contradição que o eSocial rejeita.
        """
        for rec in self:
            if not rec.ausencia_de_risco:
                continue
            if rec.utiliz_epc not in (False, "0") or rec.utiliz_epi not in (
                False,
                "0",
            ):
                raise ValidationError(
                    _(
                        "Risco %(nome)s: com o código de ausência de agente "
                        "nocivo (%(codigo)s), a utilização de EPC e de EPI deve "
                        "ser 'não se aplica'."
                    )
                    % {
                        "nome": rec.name or rec.agente_nocivo_id.name,
                        "codigo": COD_AGENTE_NOCIVO_AUSENCIA,
                    }
                )

    def _vigente_em(self, data):
        """Filtra o recordset pelos riscos vigentes na data informada."""
        data = fields.Date.to_date(data)
        return self.filtered(
            lambda r: r.date_from <= data and (not r.date_to or r.date_to >= data)
        )

    def _aplica_a_funcao(self, job):
        """Filtra o recordset pelos riscos que atingem a função informada.

        Risco sem função listada vale para o ambiente inteiro.
        """
        return self.filtered(lambda r: not r.job_ids or job in r.job_ids)

    def _aliquota_gilrat_adicional(self):
        """Maior alíquota adicional de GILRAT entre os riscos do recordset.

        A alíquota vem da Tabela 02 do eSocial: código 2 = 12% (15 anos),
        3 = 9% (20 anos), 4 = 6% (25 anos). Quando o trabalhador está exposto a
        mais de um agente ensejador, prevalece o de menor tempo de contribuição,
        que é o de maior alíquota.
        """
        aliquotas = {"2": 12.0, "3": 9.0, "4": 6.0}
        valores = [
            aliquotas.get(risco.financiamento_aposent_id.codigo, 0.0) for risco in self
        ]
        return max(valores, default=0.0)
