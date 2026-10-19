# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Alíquota RAT (Riscos Ambientais do Trabalho) — art. 22, II, Lei 8.212/91.
ALIQ_RAT = [
    ("1", "1 - 1% (risco leve)"),
    ("2", "2 - 2% (risco médio)"),
    ("3", "3 - 3% (risco grave)"),
]


class ESocialS1005(models.Model):
    _name = "l10n_br.esocial.s1005"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1005 - Tabela de Estabelecimentos"
    _order = "nr_insc_estab, ini_valid desc"

    name = fields.Char(compute="_compute_name", store=True)
    operacao = fields.Selection(
        [
            ("inclusao", "Inclusão"),
            ("alteracao", "Alteração"),
            ("exclusao", "Exclusão"),
        ],
        string="Operação",
        default="inclusao",
        required=True,
    )
    tp_insc_estab = fields.Selection(
        [
            ("1", "1 - CNPJ"),
            ("3", "3 - CAEPF"),
            ("4", "4 - CNO"),
        ],
        string="Tipo Inscrição Estabelecimento",
        default="1",
        required=True,
    )
    nr_insc_estab = fields.Char(
        string="Inscrição Estabelecimento",
        size=14,
        required=True,
        help="CNPJ (14), CAEPF (14) ou CNO (12) do estabelecimento.",
    )
    ini_valid = fields.Char(
        string="Início Validade",
        size=7,
        required=True,
        help="Formato AAAA-MM.",
    )
    fim_valid = fields.Char(
        string="Fim Validade",
        size=7,
        help="Formato AAAA-MM. Vazio significa validade em aberto.",
    )
    cnae_prep = fields.Char(
        string="CNAE Preponderante",
        size=7,
        help="CNAE preponderante do estabelecimento (7 dígitos, sem pontuação).",
    )
    cnpj_resp = fields.Char(
        string="CNPJ Responsável",
        size=14,
        help="CNPJ do responsável pela obra (uso com CNO).",
    )
    # ── GILRAT do estabelecimento (grupo aliqGilrat) ───────────────────────
    # O S-1005 leva SOMENTE RAT/FAP. FPAS, código de terceiros e terceiros
    # suspensos são da LOTAÇÃO TRIBUTÁRIA (S-1020, grupo fpasLotacao) — ver
    # l10n_br.esocial.s1020.get_parametros_encargos().
    aliq_rat = fields.Selection(
        ALIQ_RAT,
        string="Alíquota RAT",
        help="Alíquota RAT do estabelecimento conforme CNAE preponderante.",
    )
    fap = fields.Float(
        string="FAP",
        digits=(5, 4),
        help="Fator Acidentário de Prevenção (0,5000 a 2,0000) publicado pela "
        "Previdência Social para o estabelecimento.",
    )
    aliq_rat_ajust = fields.Float(
        string="RAT Ajustado (%)",
        digits=(5, 4),
        compute="_compute_aliq_rat_ajust",
        store=True,
        help="RAT x FAP — alíquota efetiva do GILRAT devida pelo estabelecimento.",
    )
    tp_caepf = fields.Selection(
        [
            ("1", "1 - Contribuinte individual"),
            ("2", "2 - Produtor rural"),
            ("3", "3 - Segurado especial"),
        ],
        string="Tipo CAEPF",
        help="Obrigatório quando o tipo de inscrição é CAEPF.",
    )
    ind_subst_patr_obra = fields.Selection(
        [
            ("1", "1 - Integralmente substituída"),
            ("2", "2 - Não substituída"),
            ("3", "3 - Parcialmente substituída"),
        ],
        string="Substituição Patronal (Obra)",
        help="Obrigatório para obra de construção civil (CNO) de construtora.",
    )
    nova_ini_valid = fields.Char(
        string="Nova Validade (Início)",
        size=7,
        help="Somente para alteração de período de validade. Formato AAAA-MM.",
    )
    nova_fim_valid = fields.Char(
        string="Nova Validade (Fim)",
        size=7,
    )

    _sql_constraints = [
        (
            "estab_validade_uniq",
            "unique(company_id, nr_insc_estab, ini_valid)",
            "Já existe um S-1005 para este estabelecimento nesta validade.",
        ),
    ]

    @api.depends("nr_insc_estab", "ini_valid")
    def _compute_name(self):
        for rec in self:
            rec.name = " - ".join(
                parte for parte in (rec.nr_insc_estab, rec.ini_valid) if parte
            )

    @api.depends("aliq_rat", "fap")
    def _compute_aliq_rat_ajust(self):
        for rec in self:
            if not rec.aliq_rat:
                rec.aliq_rat_ajust = 0.0
                continue
            # FAP ausente equivale a fator neutro 1,0000 (não zera o GILRAT).
            fator = rec.fap or 1.0
            rec.aliq_rat_ajust = float(rec.aliq_rat) * fator

    @api.constrains("fap")
    def _check_fap(self):
        for rec in self:
            if not rec.fap:
                continue
            if not 0.5 <= rec.fap <= 2.0:
                raise ValidationError(
                    _(
                        "FAP inválido (%(fap)s): o Fator Acidentário de "
                        "Prevenção vai de 0,5000 a 2,0000."
                    )
                    % {"fap": rec.fap}
                )

    @api.constrains("ini_valid", "fim_valid", "nova_ini_valid", "nova_fim_valid")
    def _check_competencias(self):
        for rec in self:
            rec._validar_competencia(rec.ini_valid, _("Início Validade"))
            rec._validar_competencia(rec.fim_valid, _("Fim Validade"))
            rec._validar_competencia(rec.nova_ini_valid, _("Nova Validade (Início)"))
            rec._validar_competencia(rec.nova_fim_valid, _("Nova Validade (Fim)"))

    def _get_event_type(self):
        return "S-1005"

    def get_parametros_encargos(self):
        """Parâmetros de GILRAT do estabelecimento.

        Contrato consumido pelo cálculo dos encargos patronais (RF-31): o
        estabelecimento responde por RAT/FAP (grupo aliqGilrat do S-1005).
        FPAS e terceiros NÃO são do estabelecimento — eles vêm da lotação
        tributária (``l10n_br.esocial.s1020.get_parametros_encargos``).
        """
        self.ensure_one()
        return {
            "nr_insc_estab": self.nr_insc_estab,
            "tp_insc_estab": self.tp_insc_estab,
            "cnae_prep": self.cnae_prep,
            "aliq_rat": float(self.aliq_rat) if self.aliq_rat else 0.0,
            "fap": self.fap or 1.0,
            "aliq_rat_ajust": self.aliq_rat_ajust,
        }

    @api.model
    def buscar_vigente(self, company, nr_insc_estab, competencia):
        """Estabelecimento vigente na competência (formato AAAA-MM).

        Vigência aberta (sem fim_valid) vale para qualquer competência a
        partir de ini_valid. Devolve o registro mais recente que cobre a
        competência, ou um recordset vazio.
        """
        candidatos = self.search(
            [
                ("company_id", "=", company.id),
                ("nr_insc_estab", "=", nr_insc_estab),
                ("operacao", "!=", "exclusao"),
                ("ini_valid", "<=", competencia),
            ],
            order="ini_valid desc",
        )
        for candidato in candidatos:
            if not candidato.fim_valid or candidato.fim_valid >= competencia:
                return candidato
        return self.browse()

    def _to_esociallib_dict(self):
        self.ensure_one()
        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "operacao": self.operacao,
            "tp_insc_estab": int(self.tp_insc_estab),
            "nr_insc_estab": self._so_digitos(self.nr_insc_estab),
            "ini_valid": self.ini_valid,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }
        if self.fim_valid:
            data["fim_valid"] = self.fim_valid

        if self.operacao == "exclusao":
            return data

        if not self.cnae_prep:
            raise UserError(
                _(
                    "Estabelecimento %(estab)s: o CNAE preponderante é "
                    "obrigatório para inclusão e alteração do S-1005."
                )
                % {"estab": self.nr_insc_estab}
            )
        data["cnae_prep"] = self._so_digitos(self.cnae_prep)

        if self.cnpj_resp:
            data["cnpj_resp"] = self._so_digitos(self.cnpj_resp)
        if self.aliq_rat:
            data["aliq_rat"] = int(self.aliq_rat)
        if self.fap:
            data["fap"] = "%.4f" % self.fap
        if self.tp_insc_estab == "3":
            if not self.tp_caepf:
                raise UserError(
                    _("Estabelecimento CAEPF exige o Tipo CAEPF preenchido.")
                )
            data["tp_caepf"] = int(self.tp_caepf)
        if self.ind_subst_patr_obra:
            data["ind_subst_patr_obra"] = int(self.ind_subst_patr_obra)

        if self.operacao == "alteracao" and self.nova_ini_valid:
            data["nova_ini_valid"] = self.nova_ini_valid
            if self.nova_fim_valid:
                data["nova_fim_valid"] = self.nova_fim_valid

        return data
