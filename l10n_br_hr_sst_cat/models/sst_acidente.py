# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_br_hr_sst.models.sst_dominios import (
    IDE_ORGAO_CLASSE_EMITENTE,
    SIM_NAO,
    TP_INSC_ESTABELECIMENTO,
)

RE_HORA = re.compile(r"^([01]\d|2[0-3])[0-5]\d$")

# evtCat/cat/tpAcid
TIPO_ACIDENTE = [
    ("1", "1 - Típico"),
    ("2", "2 - Doença ocupacional"),
    ("3", "3 - Trajeto"),
]

# evtCat/cat/iniciatCAT
INICIATIVA_CAT = [
    ("1", "1 - Iniciativa do empregador"),
    ("2", "2 - Ordem judicial"),
    ("3", "3 - Determinação de órgão fiscalizador"),
]

# evtCat/localAcidente/tpLocal
TIPO_LOCAL = [
    ("1", "1 - Estabelecimento do empregador no Brasil"),
    ("2", "2 - Estabelecimento do empregador no exterior"),
    ("3", "3 - Estabelecimento de terceiros onde o empregador presta serviços"),
    ("4", "4 - Via pública"),
    ("5", "5 - Área rural"),
    ("6", "6 - Embarcação"),
    ("9", "9 - Outros"),
]

# evtCat/parteAtingida/lateralidade
LATERALIDADE = [
    ("0", "0 - Não aplicável"),
    ("1", "1 - Esquerda"),
    ("2", "2 - Direita"),
    ("3", "3 - Ambas"),
]


class L10nBrSstAcidente(models.Model):
    """Acidente de trabalho, típico, de trajeto ou doença ocupacional.

    O registro do acidente é o que alimenta a CAT e, por ela, o S-2210. Desde
    2023 a CAT só existe pelo eSocial: o CATWeb foi descontinuado, de modo que
    sem este registro a empresa não tem como cumprir o art. 22 da Lei 8.213/91.
    """

    _name = "l10n_br.sst.acidente"
    _description = "SST - Acidente de Trabalho"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_acidente desc, id desc"

    name = fields.Char(
        string="Identificação",
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Trabalhador",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("registrado", "Registrado"),
            ("comunicado", "Comunicado"),
            ("cancelled", "Cancelado"),
        ],
        string="Situação",
        default="draft",
        required=True,
        tracking=True,
    )
    # ── Acidente ────────────────────────────────────────────────────────────
    date_acidente = fields.Date(
        string="Data do Acidente",
        required=True,
        tracking=True,
    )
    hora_acidente = fields.Char(
        string="Hora do Acidente",
        size=4,
        help="Formato HHMM, como no campo hrAcid do S-2210.",
    )
    tp_acid = fields.Selection(
        TIPO_ACIDENTE,
        string="Tipo do Acidente",
        default="1",
        required=True,
        tracking=True,
    )
    hrs_trab_antes_acid = fields.Char(
        string="Horas Trabalhadas Antes",
        size=4,
        help="Formato HHMM.",
    )
    iniciat_cat = fields.Selection(
        INICIATIVA_CAT,
        string="Iniciativa da CAT",
        default="1",
        required=True,
    )
    situacao_geradora_id = fields.Many2one(
        "l10n_br.esocial.situacao.geradora",
        string="Situação Geradora",
        required=True,
        help="Tabela 15 do eSocial.",
    )
    houve_obito = fields.Boolean(
        string="Houve Óbito",
        tracking=True,
    )
    date_obito = fields.Date(string="Data do Óbito")
    comunicacao_policia = fields.Boolean(string="Houve Comunicação à Polícia")
    houve_afastamento = fields.Boolean(
        string="Houve Afastamento do Trabalho",
        tracking=True,
    )
    ultimo_dia_trabalhado = fields.Date(string="Último Dia Trabalhado")
    observacao = fields.Text(string="Observações do Acidente")
    testemunhas = fields.Text()
    # ── Local ───────────────────────────────────────────────────────────────
    tp_local = fields.Selection(
        TIPO_LOCAL,
        string="Tipo do Local",
        default="1",
        required=True,
    )
    dsc_local = fields.Char(string="Especificação do Local")
    dsc_lograd = fields.Char(string="Logradouro")
    nr_lograd = fields.Char(string="Número")
    complemento_local = fields.Char(string="Complemento")
    bairro_local = fields.Char(string="Bairro")
    cep_local = fields.Char(string="CEP", size=8)
    city_id = fields.Many2one("res.city", string="Município")
    state_id = fields.Many2one("res.country.state", string="UF")
    country_id = fields.Many2one("res.country", string="País")
    tp_insc_local = fields.Selection(
        TP_INSC_ESTABELECIMENTO,
        string="Tipo de Inscrição do Local",
    )
    nr_insc_local = fields.Char(string="Inscrição do Local", size=14)
    # ── Lesão ───────────────────────────────────────────────────────────────
    parte_corpo_id = fields.Many2one(
        "l10n_br.esocial.parte.corpo",
        string="Parte do Corpo Atingida",
        required=True,
        help="Tabela 13 do eSocial.",
    )
    lateralidade = fields.Selection(
        LATERALIDADE,
        default="0",
        required=True,
    )
    agente_causador_id = fields.Many2one(
        "l10n_br.esocial.agente.causador",
        string="Agente Causador",
        required=True,
        help="Tabela 14 do eSocial.",
    )
    natureza_lesao_id = fields.Many2one(
        "l10n_br.esocial.natureza.lesao",
        string="Natureza da Lesão",
        help="Tabela 17 do eSocial.",
    )
    cid_id = fields.Many2one(
        "l10n_br.esocial.cid",
        string="CID",
    )
    # ── Atestado médico ─────────────────────────────────────────────────────
    date_atendimento = fields.Date(string="Data do Atendimento")
    hora_atendimento = fields.Char(
        string="Hora do Atendimento",
        size=4,
        help="Formato HHMM.",
    )
    ind_internacao = fields.Selection(
        SIM_NAO,
        string="Houve Internação",
        default="N",
    )
    dur_trat = fields.Integer(string="Duração do Tratamento (dias)")
    ind_afast = fields.Selection(
        SIM_NAO,
        string="Afastamento do Trabalho",
        default="N",
    )
    dsc_comp_lesao = fields.Char(string="Descrição Complementar da Lesão")
    diagnostico_provavel = fields.Char(string="Diagnóstico Provável")
    observacao_atestado = fields.Char(string="Observação do Atestado")
    nm_emit = fields.Char(string="Emitente do Atestado")
    ide_oc_emit = fields.Selection(
        IDE_ORGAO_CLASSE_EMITENTE,
        string="Órgão de Classe do Emitente",
    )
    nr_oc_emit = fields.Char(string="Número no Órgão de Classe")
    uf_oc_emit = fields.Char(string="UF do Órgão de Classe", size=2)
    # ── Desdobramentos ──────────────────────────────────────────────────────
    cat_ids = fields.One2many(
        "l10n_br.sst.cat",
        "acidente_id",
        string="CATs",
    )
    cat_count = fields.Integer(string="CATs", compute="_compute_cat_count")
    afastamento_id = fields.Many2one(
        "l10n_br.esocial.s2230",
        string="Afastamento (S-2230)",
        readonly=True,
        help="Afastamento gerado a partir deste acidente.",
    )

    @api.depends("employee_id", "date_acidente")
    def _compute_name(self):
        for rec in self:
            partes = [
                rec.employee_id.name,
                rec.date_acidente and str(rec.date_acidente),
            ]
            rec.name = " - ".join(p for p in partes if p)

    @api.depends("cat_ids")
    def _compute_cat_count(self):
        for rec in self:
            rec.cat_count = len(rec.cat_ids)

    @api.constrains("hora_acidente", "hrs_trab_antes_acid", "hora_atendimento")
    def _check_horas(self):
        rotulos = {
            "hora_acidente": _("Hora do Acidente"),
            "hrs_trab_antes_acid": _("Horas Trabalhadas Antes"),
            "hora_atendimento": _("Hora do Atendimento"),
        }
        for rec in self:
            for campo, rotulo in rotulos.items():
                valor = rec[campo]
                if valor and not RE_HORA.match(valor):
                    raise ValidationError(
                        _(
                            "%(rotulo)s inválida: %(valor)r. O eSocial espera o "
                            "formato HHMM, por exemplo 1430."
                        )
                        % {"rotulo": rotulo, "valor": valor}
                    )

    @api.constrains("houve_obito", "date_obito", "date_acidente")
    def _check_obito(self):
        for rec in self:
            if rec.houve_obito and not rec.date_obito:
                raise ValidationError(
                    _("Acidente de %(nome)s: informe a data do óbito.")
                    % {"nome": rec.employee_id.name}
                )
            if rec.date_obito and rec.date_obito < rec.date_acidente:
                raise ValidationError(
                    _("Acidente de %(nome)s: o óbito é anterior ao acidente.")
                    % {"nome": rec.employee_id.name}
                )

    @api.onchange("houve_afastamento")
    def _onchange_houve_afastamento(self):
        if self.houve_afastamento:
            self.ind_afast = "S"

    def action_registrar(self):
        """Registra o acidente e já abre a CAT inicial."""
        for rec in self:
            if rec.state != "draft":
                continue
            rec.state = "registrado"
            if not rec.cat_ids:
                rec._criar_cat("1")
        return True

    def _criar_cat(self, codigo_tipo):
        self.ensure_one()
        tipo = self.env["l10n_br.esocial.tipo.cat"].search(
            [("codigo", "=", codigo_tipo)], limit=1
        )
        if not tipo:
            raise UserError(
                _("Tipo de CAT %(codigo)s não encontrado na tabela do eSocial.")
                % {"codigo": codigo_tipo}
            )
        valores = {"acidente_id": self.id, "tipo_cat_id": tipo.id}
        if codigo_tipo in ("2", "3"):
            # Reabertura e óbito referenciam a comunicação anterior. Sem isso o
            # eSocial rejeita, e a constraint local barra antes.
            origem = self.cat_ids.filtered(
                lambda c: c.tipo_cat_codigo == "1" and c.state != "cancelled"
            )[:1]
            if not origem:
                raise UserError(
                    _(
                        "Acidente de %(nome)s: emita a CAT inicial antes da "
                        "CAT de reabertura ou de comunicação de óbito."
                    )
                    % {"nome": self.employee_id.name}
                )
            valores["cat_origem_id"] = origem.id
        return self.env["l10n_br.sst.cat"].create(valores)

    def action_criar_cat_reabertura(self):
        self.ensure_one()
        return self._criar_cat("2")

    def action_criar_cat_obito(self):
        self.ensure_one()
        if not self.houve_obito:
            raise UserError(
                _(
                    "Acidente de %(nome)s: marque o óbito e informe a data "
                    "antes de emitir a CAT de comunicação de óbito."
                )
                % {"nome": self.employee_id.name}
            )
        return self._criar_cat("3")

    def action_gerar_afastamento(self):
        """Cria o afastamento (S-2230) vinculado, com o motivo de acidente.

        O motivo é o código 01 da Tabela 18, "acidente/doença do trabalho", e
        vale para as três espécies que geram CAT: típico, de trajeto e doença
        ocupacional. O código 03 é justamente o oposto, acidente ou doença NÃO
        relacionada ao trabalho, e usá-lo aqui destruiria o nexo com o acidente.
        """
        self.ensure_one()
        if self.afastamento_id:
            return self.afastamento_id
        if not self.houve_afastamento:
            raise UserError(
                _(
                    "Acidente de %(nome)s: marque que houve afastamento antes "
                    "de gerar o S-2230."
                )
                % {"nome": self.employee_id.name}
            )
        codigo = "01"
        motivo = self.env["l10n_br.esocial.motivo.afastamento"].search(
            [("codigo", "=", codigo)], limit=1
        )
        afastamento = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee_id.id,
                "company_id": self.company_id.id,
                "dt_ini_afast": self.ultimo_dia_trabalhado or self.date_acidente,
                "cod_mot_afast": motivo.codigo if motivo else codigo,
                "motivo_afastamento_id": motivo.id if motivo else False,
            }
        )
        self.afastamento_id = afastamento
        return afastamento

    def action_cancelar(self):
        self.write({"state": "cancelled"})

    def action_view_cats(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_br_hr_sst_cat.l10n_br_sst_cat_action"
        )
        action["domain"] = [("acidente_id", "=", self.id)]
        action["context"] = {"default_acidente_id": self.id}
        return action
