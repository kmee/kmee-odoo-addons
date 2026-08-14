# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Códigos de tpExameOcup do S-2220 (enum ExMedOcupTpExameOcup do leiaute).
TIPO_ASO_ADMISSIONAL = "0"
TIPO_ASO_PERIODICO = "1"
TIPO_ASO_RETORNO = "2"
TIPO_ASO_MUDANCA_RISCO = "3"
TIPO_ASO_PONTUAL = "4"
TIPO_ASO_DEMISSIONAL = "9"

RESULTADO_ASO = [
    ("1", "1 - Apto"),
    ("2", "2 - Inapto"),
]

# evtMonit/exame/ordExame e indResult
ORDEM_EXAME = [
    ("1", "1 - Inicial"),
    ("2", "2 - Sequencial"),
]
INDICATIVO_RESULTADO = [
    ("1", "1 - Normal"),
    ("2", "2 - Alterado"),
    ("3", "3 - Estável"),
    ("4", "4 - Agravamento"),
]


class HrEmployeeMedicalExamination(models.Model):
    """ASO brasileiro sobre o exame médico da OCA.

    O modelo da OCA guarda data, resultado aprovado/reprovado e nota. O ASO da
    NR-7 e o evento S-2220 pedem bem mais: tipo de exame, médico emitente com
    CRM, exames complementares com procedimento da Tabela 27 e vencimento.

    Sigilo (LGPD art. 11): o ASO registra apenas apto ou inapto. Tudo o que for
    dado clínico fica em campo restrito ao grupo de saúde ocupacional, fora do
    alcance do RH.
    """

    _inherit = "hr.employee.medical.examination"

    l10n_br_tipo_aso_id = fields.Many2one(
        "l10n_br.esocial.tipo.aso",
        string="Tipo de ASO",
        tracking=True,
    )
    l10n_br_tipo_aso_codigo = fields.Char(
        related="l10n_br_tipo_aso_id.codigo",
        string="Código do Tipo de ASO",
        store=True,
    )
    l10n_br_resultado = fields.Selection(
        RESULTADO_ASO,
        string="Resultado do ASO",
        tracking=True,
        help="Campo resAso do S-2220. O leiaute só admite apto ou inapto; a "
        "restrição, quando houver, é registrada à parte.",
    )
    l10n_br_com_restricao = fields.Boolean(
        string="Apto com Restrição",
        tracking=True,
    )
    l10n_br_restricao = fields.Char(
        string="Descrição da Restrição",
        help="Restrição funcional comunicada ao empregador, sem diagnóstico.",
    )
    l10n_br_medico_nome = fields.Char(
        string="Médico Emitente",
        tracking=True,
    )
    l10n_br_crm = fields.Char(
        string="CRM",
    )
    l10n_br_uf_crm = fields.Char(
        string="UF do CRM",
        size=2,
    )
    l10n_br_clinica_id = fields.Many2one(
        "res.partner",
        string="Clínica",
    )
    l10n_br_pcmso_id = fields.Many2one(
        "l10n_br.sst.pcmso",
        string="PCMSO",
    )
    l10n_br_date_vencimento = fields.Date(
        string="Vencimento",
        tracking=True,
        help="Data em que o próximo exame periódico se torna devido.",
    )
    l10n_br_exame_ids = fields.One2many(
        "l10n_br.sst.exame.complementar",
        "examination_id",
        string="Exames Complementares",
    )
    l10n_br_observacao_clinica = fields.Text(
        string="Observação Clínica",
        groups="l10n_br_hr_sst_aso.group_sst_medico",
        help="Informação clínica sob sigilo médico. Não sai no ASO nem no "
        "evento do eSocial e não é visível ao RH.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )

    @api.constrains("l10n_br_com_restricao", "l10n_br_resultado")
    def _check_restricao(self):
        for rec in self:
            if rec.l10n_br_com_restricao and rec.l10n_br_resultado == "2":
                raise ValidationError(
                    _(
                        "Exame de %(nome)s: trabalhador inapto não é apto com "
                        "restrição. Escolha um dos dois."
                    )
                    % {"nome": rec.employee_id.name}
                )

    @api.onchange("l10n_br_resultado")
    def _onchange_l10n_br_resultado(self):
        """Mantém o resultado da OCA alinhado ao resultado brasileiro."""
        for rec in self:
            if rec.l10n_br_resultado:
                rec.result = "passed" if rec.l10n_br_resultado == "1" else "failed"

    def _l10n_br_periodicidade_meses(self):
        """Meses até o próximo periódico, conforme o PCMSO vigente.

        Exame antigo, anterior ao programa em vigor, cai para o PCMSO de hoje:
        quem manda na periodicidade é o programa vigente, não o do passado.
        """
        self.ensure_one()
        company = self.employee_id.company_id or self.env.company
        pcmso_model = self.env["l10n_br.sst.pcmso"]
        pcmso = (
            self.l10n_br_pcmso_id
            or pcmso_model.buscar_vigente(company, self.date)
            or pcmso_model.buscar_vigente(company)
        )
        if not pcmso:
            return 0
        return pcmso.periodicidade_do_empregado(self.employee_id, self.date)

    def _l10n_br_calcula_vencimento(self):
        """Calcula o vencimento do ASO a partir da periodicidade do PCMSO.

        O demissional não gera vencimento: o vínculo acabou.
        """
        for rec in self:
            if not rec.date or rec.l10n_br_tipo_aso_codigo == TIPO_ASO_DEMISSIONAL:
                continue
            meses = rec._l10n_br_periodicidade_meses()
            if not meses:
                continue
            rec.l10n_br_date_vencimento = rec.date + relativedelta(months=meses)

    def to_done(self):
        """Conclui o exame exigindo o mínimo que o ASO e o S-2220 pedem."""
        for rec in self:
            faltando = []
            if not rec.l10n_br_tipo_aso_id:
                faltando.append(_("tipo de ASO"))
            if not rec.date:
                faltando.append(_("data do exame"))
            if not rec.l10n_br_resultado:
                faltando.append(_("resultado (apto ou inapto)"))
            if not rec.l10n_br_medico_nome:
                faltando.append(_("médico emitente"))
            if faltando:
                raise UserError(
                    _(
                        "Não é possível concluir o exame de %(nome)s sem "
                        "informar: %(campos)s."
                    )
                    % {
                        "nome": rec.employee_id.name,
                        "campos": ", ".join(faltando),
                    }
                )
        res = super().to_done()
        self._l10n_br_calcula_vencimento()
        return res

    @api.model
    def l10n_br_gerar_aso(self, employee, tipo_codigo, date=None, pcmso=None):
        """Cria um ASO pendente do tipo informado para o trabalhador.

        Args:
            employee: recordset de ``hr.employee`` (um registro).
            tipo_codigo: código de ``tpExameOcup`` (0, 1, 2, 3, 4 ou 9).
            date: data prevista; ``None`` usa hoje.
            pcmso: PCMSO a vincular; ``None`` busca o vigente.

        Returns:
            O exame criado.
        """
        employee.ensure_one()
        date = fields.Date.to_date(date) or fields.Date.context_today(employee)
        tipo = self.env["l10n_br.esocial.tipo.aso"].search(
            [("codigo", "=", tipo_codigo)], limit=1
        )
        if not pcmso:
            company = employee.company_id or self.env.company
            pcmso_model = self.env["l10n_br.sst.pcmso"]
            pcmso = pcmso_model.buscar_vigente(
                company, date
            ) or pcmso_model.buscar_vigente(company)
        return self.create(
            {
                "name": _("ASO %(tipo)s - %(nome)s")
                % {
                    "tipo": tipo.nome or tipo_codigo,
                    "nome": employee.name,
                },
                "employee_id": employee.id,
                "date": date,
                "l10n_br_tipo_aso_id": tipo.id,
                "l10n_br_pcmso_id": pcmso.id if pcmso else False,
            }
        )

    @api.model
    def cron_agendar_periodicos(self, dias_antecedencia=30):
        """Agenda o exame periódico de quem está com o ASO a vencer (NR-7).

        Cria um exame pendente por trabalhador, e nunca um segundo enquanto o
        primeiro não for concluído ou cancelado.
        """
        hoje = fields.Date.context_today(self)
        limite = hoje + relativedelta(days=dias_antecedencia)
        vencendo = self.search(
            [
                ("state", "=", "done"),
                ("l10n_br_date_vencimento", "!=", False),
                ("l10n_br_date_vencimento", "<=", limite),
            ]
        )
        criados = self.browse()
        for exame in vencendo:
            employee = exame.employee_id
            if not employee.contract_id or employee.contract_id.state != "open":
                continue
            pendente = self.search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("state", "=", "pending"),
                ]
            )
            if pendente:
                continue
            criados |= self.l10n_br_gerar_aso(
                employee,
                TIPO_ASO_PERIODICO,
                date=exame.l10n_br_date_vencimento,
            )
        return criados


class L10nBrSstExameComplementar(models.Model):
    """Exame complementar do ASO (grupo exame do S-2220)."""

    _name = "l10n_br.sst.exame.complementar"
    _description = "SST - Exame Complementar do ASO"
    _order = "date, id"

    examination_id = fields.Many2one(
        "hr.employee.medical.examination",
        string="ASO",
        required=True,
        ondelete="cascade",
    )
    procedimento_id = fields.Many2one(
        "l10n_br.esocial.procedimento.diagnostico",
        string="Procedimento",
        required=True,
        help="Procedimento diagnóstico da Tabela 27 do eSocial.",
    )
    date = fields.Date(
        string="Data do Exame",
        required=True,
        default=fields.Date.context_today,
    )
    ord_exame = fields.Selection(
        ORDEM_EXAME,
        string="Ordem",
        default="1",
    )
    ind_result = fields.Selection(
        INDICATIVO_RESULTADO,
        string="Indicativo do Resultado",
    )
    observacao = fields.Char(string="Observação")

    def _to_exame(self):
        """Dicionário do grupo exame consumido pelo intermediário S-2220."""
        self.ensure_one()
        dados = {
            "dt_exm": str(self.date),
            "proc_realizado": self.procedimento_id.codigo,
        }
        if self.ord_exame:
            dados["ord_exame"] = int(self.ord_exame)
        if self.ind_result:
            dados["ind_result"] = int(self.ind_result)
        if self.observacao:
            dados["obs_proc"] = self.observacao
        return dados
