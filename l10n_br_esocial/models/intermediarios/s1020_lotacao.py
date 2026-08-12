# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Classificações tributárias do Simples Nacional e MEI (Tabela 8). Nelas a
# contribuição para terceiros é dispensada SEMPRE, inclusive no anexo IV
# (LC 123/2006 art. 13, § 3º), então codTercs tem de ser 0000.
CLASS_TRIB_SIMPLES = ("01", "02", "03", "04")
COD_TERCS_DISPENSADO = "0000"


class ESocialS1020(models.Model):
    _name = "l10n_br.esocial.s1020"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1020 - Tabela de Lotações Tributárias"
    _order = "cod_lotacao, ini_valid desc"

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
    cod_lotacao = fields.Char(
        string="Código Lotação",
        size=30,
        required=True,
    )
    ini_valid = fields.Char(
        string="Início Validade",
        size=7,
        required=True,
        help="Formato AAAA-MM",
    )
    fim_valid = fields.Char(
        string="Fim Validade",
        size=7,
    )
    # ── fpasLotacao: FPAS e terceiros são da LOTAÇÃO, não do estabelecimento ─
    fpas = fields.Char(
        string="FPAS",
        size=3,
        help="Código FPAS da lotação (Tabela 4). Define o conjunto de "
        "contribuições de terceiros devidas.",
    )
    cod_tercs = fields.Char(
        string="Código Terceiros",
        size=4,
        help="Código de terceiros associado ao FPAS (SESC/SENAI/SEBRAE/INCRA/"
        "salário-educação). Empresa do Simples Nacional informa 0000: "
        "terceiros são dispensados (LC 123/2006 art. 13, § 3º).",
    )
    cod_tercs_susp = fields.Char(
        string="Terceiros Suspensos",
        size=4,
        help="Código de terceiros com contribuição suspensa por decisão "
        "administrativa ou judicial.",
    )

    _sql_constraints = [
        (
            "lotacao_validade_uniq",
            "unique(company_id, cod_lotacao, ini_valid)",
            "Já existe um S-1020 para esta lotação nesta validade.",
        ),
    ]

    @api.depends("cod_lotacao", "ini_valid")
    def _compute_name(self):
        for rec in self:
            rec.name = " - ".join(
                parte for parte in (rec.cod_lotacao, rec.ini_valid) if parte
            )

    @api.constrains("ini_valid", "fim_valid")
    def _check_competencias(self):
        for rec in self:
            rec._validar_competencia(rec.ini_valid, _("Início Validade"))
            rec._validar_competencia(rec.fim_valid, _("Fim Validade"))

    def _get_event_type(self):
        return "S-1020"

    def get_parametros_encargos(self):
        """Parâmetros de FPAS e terceiros da lotação tributária.

        Contrato consumido pelo cálculo dos encargos patronais (RF-31). O
        GILRAT (RAT/FAP) NÃO está aqui: ele é do estabelecimento, no S-1005
        (``l10n_br.esocial.s1005.get_parametros_encargos``).
        """
        self.ensure_one()
        return {
            "cod_lotacao": self.cod_lotacao,
            "tp_lotacao": self.company_id.l10n_br_esocial_lotacao_id.codigo,
            "fpas": self.fpas,
            "cod_tercs": self.cod_tercs,
            "cod_tercs_susp": self.cod_tercs_susp,
            "terceiros_dispensados": self._terceiros_dispensados(),
        }

    @api.model
    def buscar_vigente(self, company, cod_lotacao, competencia):
        """Lotação vigente na competência (formato AAAA-MM).

        Vigência aberta (sem fim_valid) vale de ini_valid em diante. Devolve o
        registro mais recente que cobre a competência, ou recordset vazio.
        """
        candidatos = self.search(
            [
                ("company_id", "=", company.id),
                ("cod_lotacao", "=", cod_lotacao),
                ("operacao", "!=", "exclusao"),
                ("ini_valid", "<=", competencia),
            ],
            order="ini_valid desc",
        )
        for candidato in candidatos:
            if not candidato.fim_valid or candidato.fim_valid >= competencia:
                return candidato
        return self.browse()

    def _terceiros_dispensados(self):
        """Empresa do Simples/MEI não recolhe terceiros (LC 123 art. 13 § 3º)."""
        self.ensure_one()
        codigo = self.company_id.l10n_br_esocial_class_trib_id.codigo
        return codigo in CLASS_TRIB_SIMPLES

    def _to_esociallib_dict(self):
        self.ensure_one()
        company = self.company_id

        if not company.l10n_br_esocial_lotacao_id:
            raise UserError(
                _(
                    "Empresa '%(name)s' não possui Tipo de Lotação Tributária "
                    "eSocial configurada."
                )
                % {"name": company.name}
            )

        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "operacao": self.operacao,
            "cod_lotacao": self.cod_lotacao,
            "ini_valid": self.ini_valid,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }

        if self.fim_valid:
            data["fim_valid"] = self.fim_valid

        if self.operacao in ("inclusao", "alteracao"):
            # FPAS e terceiros definem a contribuição devida: não podem cair em
            # valor-padrão silencioso.
            if not self.fpas:
                raise UserError(
                    _(
                        "Lotação %(lotacao)s: informe o código FPAS. Ele define "
                        "as contribuições de terceiros devidas e não pode ser "
                        "assumido por padrão."
                    )
                    % {"lotacao": self.cod_lotacao}
                )
            dispensado = self._terceiros_dispensados()
            cod_tercs = self.cod_tercs or (
                COD_TERCS_DISPENSADO if dispensado else False
            )
            if not cod_tercs:
                raise UserError(
                    _(
                        "Lotação %(lotacao)s: informe o código de terceiros "
                        "correspondente ao FPAS %(fpas)s (use 0000 quando não "
                        "houver contribuição de terceiros devida)."
                    )
                    % {"lotacao": self.cod_lotacao, "fpas": self.fpas}
                )
            if dispensado and cod_tercs != COD_TERCS_DISPENSADO:
                raise UserError(
                    _(
                        "Empresa enquadrada no Simples Nacional (classificação "
                        "tributária %(class_trib)s) não recolhe contribuição "
                        "para terceiros (LC 123/2006 art. 13, § 3º): o código "
                        "de terceiros da lotação %(lotacao)s deve ser 0000, e "
                        "não %(cod_tercs)s."
                    )
                    % {
                        "class_trib": (company.l10n_br_esocial_class_trib_id.codigo),
                        "lotacao": self.cod_lotacao,
                        "cod_tercs": cod_tercs,
                    }
                )
            data["tp_lotacao"] = company.l10n_br_esocial_lotacao_id.codigo
            data["fpas"] = self.fpas
            data["cod_tercs"] = cod_tercs
            if self.cod_tercs_susp:
                data["cod_tercs_susp"] = self.cod_tercs_susp

        return data
