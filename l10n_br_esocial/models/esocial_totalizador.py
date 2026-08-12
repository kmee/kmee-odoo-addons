# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

try:
    from esociallib.retorno_totalizadores import parse_totalizadores
except ImportError:
    parse_totalizadores = None
    _logger.warning(
        "esociallib sem retorno_totalizadores: os eventos totalizadores do "
        "eSocial não serão persistidos."
    )

TIPO_TOTALIZADOR = [
    ("S-5001", "S-5001 - Bases e valores por trabalhador"),
    ("S-5002", "S-5002 - IRRF por beneficiário"),
    ("S-5003", "S-5003 - Bases do FGTS por trabalhador"),
    ("S-5011", "S-5011 - Contribuições sociais consolidadas"),
    ("S-5012", "S-5012 - IRRF consolidado"),
    ("S-5013", "S-5013 - FGTS consolidado"),
]

GRUPO_LINHA = [
    ("info_cp_calc", "Contribuição previdenciária calculada"),
    ("base_cs", "Base de contribuição social"),
    ("calc_terc", "Contribuição de terceiros"),
    ("base_pis_pasep", "Base PIS/PASEP"),
    ("cp_seg", "Contribuição do segurado (consolidada)"),
    ("base_cp", "Base de contribuição previdenciária"),
    ("base_cp13", "Base de contribuição previdenciária (13º)"),
    ("cr_estab", "Código de receita por estabelecimento"),
    ("cr_contrib", "Código de receita do contribuinte"),
    ("cr_men", "Código de receita mensal (IRRF)"),
    ("cr_dia", "Código de receita diário (IRRF)"),
]


class ESocialTotalizador(models.Model):
    """Evento totalizador devolvido pelo eSocial.

    Os totalizadores não são gerados pelo empregador: eles voltam do governo
    quando um evento periódico é processado e são a fonte OFICIAL do que foi
    apurado e enviado para a DCTFWeb. Por isso são persistidos como registros
    consultáveis, ligados ao evento de origem, e nunca recalculados.
    """

    _name = "l10n_br.esocial.totalizador"
    _description = "eSocial - Evento Totalizador"
    _order = "per_apur desc, tipo, id"

    name = fields.Char(compute="_compute_name", store=True)
    tipo = fields.Selection(
        TIPO_TOTALIZADOR,
        required=True,
        index=True,
    )
    evento_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Evento de Origem",
        required=True,
        ondelete="cascade",
        index=True,
        help="Evento periódico cujo processamento gerou este totalizador.",
    )
    evento_tipo = fields.Char(
        string="Tipo do Evento de Origem",
        related="evento_id.tipo",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        index=True,
    )
    ind_apuracao = fields.Selection(
        [
            ("1", "Mensal"),
            ("2", "Anual (13º Salário)"),
        ],
        string="Tipo Apuração",
    )
    nr_rec_arq_base = fields.Char(
        string="Recibo do Arquivo Base",
        help="Recibo do evento que originou o totalizador. É a chave oficial "
        "que liga a apuração do governo ao evento transmitido.",
    )
    cpf_trab = fields.Char(string="CPF do Trabalhador", size=11, index=True)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Trabalhador",
        ondelete="set null",
        help="Resolvido pelo CPF devolvido no totalizador.",
    )
    ind_exist_info = fields.Char(
        string="Indicativo de Existência de Informação",
        size=1,
    )
    id_evento = fields.Char(string="ID do Totalizador")
    xml = fields.Text(string="XML do Totalizador")
    linha_ids = fields.One2many(
        "l10n_br.esocial.totalizador.linha",
        "totalizador_id",
        string="Valores",
    )
    linha_count = fields.Integer(compute="_compute_linha_count")

    @api.depends("tipo", "per_apur", "cpf_trab")
    def _compute_name(self):
        for rec in self:
            partes = [rec.tipo or "", rec.per_apur or ""]
            if rec.cpf_trab:
                partes.append(rec.cpf_trab)
            rec.name = " ".join(parte for parte in partes if parte)

    @api.depends("linha_ids")
    def _compute_linha_count(self):
        for rec in self:
            rec.linha_count = len(rec.linha_ids)

    @api.model
    def criar_do_retorno(self, evento, retorno_xml):
        """Cria (ou recria) os totalizadores do retorno de um evento.

        Idempotente: uma nova consulta do mesmo lote substitui os
        totalizadores anteriores do evento, em vez de duplicá-los.
        """
        if parse_totalizadores is None:
            return self.browse()
        totalizadores = parse_totalizadores(retorno_xml)
        if not totalizadores:
            return self.browse()

        existentes = self.search([("evento_id", "=", evento.id)])
        if existentes:
            existentes.unlink()

        criados = self.browse()
        for totalizador in totalizadores:
            criados |= self.create(self._vals_do_parser(evento, totalizador))
        _logger.info(
            "eSocial evento %s: %s totalizador(es) persistido(s) (%s).",
            evento.id,
            len(criados),
            ", ".join(criados.mapped("tipo")),
        )
        return criados

    @api.model
    def _vals_do_parser(self, evento, totalizador):
        """Traduz uma dataclass Totalizador da esociallib em valores do modelo."""
        cpf = totalizador.cpf_trab or False
        return {
            "tipo": totalizador.evento,
            "evento_id": evento.id,
            "company_id": evento.company_id.id,
            "per_apur": totalizador.per_apur or evento.per_apur or False,
            "ind_apuracao": totalizador.ind_apuracao or False,
            "nr_rec_arq_base": totalizador.nr_rec_arq_base or False,
            "cpf_trab": cpf,
            "employee_id": self._buscar_employee(evento.company_id, cpf).id or False,
            "ind_exist_info": totalizador.ind_exist_info or False,
            "id_evento": totalizador.id_evento or False,
            "xml": totalizador.xml or False,
            "linha_ids": [
                (
                    0,
                    0,
                    {
                        "grupo": linha.grupo,
                        "codigo": linha.codigo or False,
                        "descricao": linha.descricao or False,
                        "valor": float(linha.valor),
                        "matricula": linha.matricula or False,
                        "cod_categ": linha.cod_categ or False,
                        "cod_lotacao": linha.cod_lotacao or False,
                        "tp_insc": linha.tp_insc or False,
                        "nr_insc": linha.nr_insc or False,
                        "ind_13": linha.ind_13 or False,
                        "per_ref": linha.per_ref or False,
                    },
                )
                for linha in totalizador.linhas
            ],
        }

    @api.model
    def _buscar_employee(self, company, cpf):
        """Empregado da empresa cujo CPF (só dígitos) casa com o devolvido."""
        employees = self.env["hr.employee"]
        if not cpf:
            return employees
        candidatos = employees.search(
            [("company_id", "in", (company.id, False)), ("cnpj_cpf", "!=", False)]
        )
        for employee in candidatos:
            digitos = "".join(c for c in employee.cnpj_cpf if c.isdigit())
            if digitos == cpf:
                return employee
        return employees

    @api.model
    def total_por_grupo(self, dominio, grupo, codigo=None, descricao=None):
        """Soma os valores de um grupo nos totalizadores que casam o domínio.

        É o acesso usado pela conferência da competência: sempre parte do que o
        governo devolveu, nunca de recálculo local.
        """
        dominio_linha = [("totalizador_id", "in", self.search(dominio).ids)]
        dominio_linha.append(("grupo", "=", grupo))
        if codigo is not None:
            dominio_linha.append(("codigo", "=", codigo))
        if descricao is not None:
            dominio_linha.append(("descricao", "=", descricao))
        linhas = self.env["l10n_br.esocial.totalizador.linha"].search(dominio_linha)
        return sum(linhas.mapped("valor"))

    def action_ver_linhas(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Valores do Totalizador"),
            "res_model": "l10n_br.esocial.totalizador.linha",
            "view_mode": "tree",
            "domain": [("totalizador_id", "=", self.id)],
        }


class ESocialTotalizadorLinha(models.Model):
    _name = "l10n_br.esocial.totalizador.linha"
    _description = "eSocial - Valor de Totalizador"
    _order = "totalizador_id, grupo, codigo, id"

    totalizador_id = fields.Many2one(
        "l10n_br.esocial.totalizador",
        string="Totalizador",
        required=True,
        ondelete="cascade",
        index=True,
    )
    tipo = fields.Selection(
        related="totalizador_id.tipo",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="totalizador_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="totalizador_id.currency_id",
        readonly=True,
    )
    per_apur = fields.Char(
        related="totalizador_id.per_apur",
        store=True,
        readonly=True,
    )
    employee_id = fields.Many2one(
        related="totalizador_id.employee_id",
        store=True,
        readonly=True,
    )
    grupo = fields.Selection(
        GRUPO_LINHA,
        required=True,
        index=True,
    )
    codigo = fields.Char(
        string="Código",
        index=True,
        help="Código de receita (tpCR/CRMen/CRDia) ou tipo de valor, conforme "
        "o grupo.",
    )
    descricao = fields.Char(
        string="Campo",
        help="Campo do leiaute que originou o valor (ex.: vrBcCp00, vrDescSeg).",
    )
    valor = fields.Monetary(
        currency_field="currency_id",
    )
    matricula = fields.Char(string="Matrícula", size=30)
    cod_categ = fields.Char(string="Categoria", size=3)
    cod_lotacao = fields.Char(string="Lotação", size=30)
    tp_insc = fields.Char(string="Tipo Inscrição", size=1)
    nr_insc = fields.Char(string="Inscrição", size=14)
    ind_13 = fields.Char(string="Indicativo 13º", size=1)
    per_ref = fields.Char(string="Período Referência", size=7)
