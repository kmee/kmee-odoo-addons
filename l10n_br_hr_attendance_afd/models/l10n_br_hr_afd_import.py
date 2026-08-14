# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import afd_layout, afd_parser

_logger = logging.getLogger(__name__)


class L10nBrHrAfdImport(models.Model):
    """Lote de importação de AFD.

    Um registro por arquivo lido. Guarda o que foi aceito, o que foi recusado e
    o porquê - a importação nunca descarta marcação em silêncio, porque um
    registro perdido aqui é jornada não paga lá na frente.
    """

    _name = "l10n_br.hr.afd.import"
    _description = "Importação de AFD"
    _order = "create_date desc"
    _inherit = ["mail.thread"]

    name = fields.Char(
        required=True,
        default=lambda self: _("Nova importação"),
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    arquivo = fields.Binary(
        string="Arquivo AFD",
        required=True,
        attachment=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    arquivo_nome = fields.Char(string="Nome do arquivo")
    rep_id = fields.Many2one(
        comodel_name="l10n_br.hr.rep",
        string="REP de origem",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="rep_id.company_id",
        store=True,
    )
    leiaute = fields.Selection(
        selection=[
            ("auto", "Detectar automaticamente"),
            ("671", "Portaria 671/2021 (Anexo V)"),
            ("1510", "Portaria 1.510/2009 (legado)"),
        ],
        default="auto",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    fuso_horas = fields.Float(
        string="Fuso do estabelecimento",
        default=-3.0,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Usado somente no leiaute 1.510, que grava hora local sem fuso. "
        "No leiaute 671 o fuso vem em cada marcação.",
    )
    leiaute_detectado = fields.Char(readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Rascunho"),
            ("analisado", "Analisado"),
            ("importado", "Importado"),
            ("erro", "Com erro"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    hash_arquivo = fields.Char(
        string="SHA-256 do arquivo",
        readonly=True,
        index=True,
        help="Impressão digital do conteúdo, usada para reconhecer "
        "reimportação do mesmo arquivo.",
    )
    nsr_inicial = fields.Integer(readonly=True)
    nsr_final = fields.Integer(readonly=True)
    qtd_marcacoes = fields.Integer(string="Marcações no arquivo", readonly=True)
    qtd_importadas = fields.Integer(string="Marcações importadas", readonly=True)
    qtd_duplicadas = fields.Integer(
        string="Já existentes", readonly=True, help="NSRs que já estavam na base."
    )
    qtd_pendentes = fields.Integer(
        string="Sem funcionário",
        readonly=True,
        help="Marcações cujo CPF/PIS não bateu com nenhum funcionário.",
    )
    qtd_eventos = fields.Integer(string="Eventos do REP", readonly=True)
    lacunas_nsr = fields.Text(
        string="Lacunas de NSR",
        readonly=True,
        help="Faixas ausentes na sequência. Lacuna é indício de marcação "
        "suprimida e trava o fechamento da competência.",
    )
    tem_lacuna = fields.Boolean(compute="_compute_tem_lacuna", store=True)
    log = fields.Text(string="Ocorrências", readonly=True)
    marcacao_ids = fields.One2many(
        comodel_name="l10n_br.hr.marcacao",
        inverse_name="afd_import_id",
        string="Marcações do lote",
        readonly=True,
    )

    @api.depends("lacunas_nsr")
    def _compute_tem_lacuna(self):
        for rec in self:
            rec.tem_lacuna = bool(rec.lacunas_nsr)

    def _conteudo_texto(self):
        """Decodifica o anexo em ISO-8859-1, como manda o Anexo V."""
        self.ensure_one()
        if not self.arquivo:
            raise UserError(_("Anexe o arquivo AFD antes de analisar."))
        bruto = base64.b64decode(self.arquivo)
        return bruto.decode(afd_layout.ENCODING_AFD, errors="replace"), bruto

    def action_analisar(self):
        """Lê o arquivo e mostra o diagnóstico ANTES de gravar qualquer coisa.

        Separar análise de importação existe por um motivo concreto: um AFD com
        CRC divergente ou lacuna de NSR precisa de decisão humana, e essa
        decisão fica melhor informada antes de a base ter os dados.
        """
        for rec in self:
            conteudo, bruto = rec._conteudo_texto()
            leiaute = None if rec.leiaute == "auto" else rec.leiaute
            resultado = afd_parser.ler_afd(
                conteudo, leiaute=leiaute, fuso_horas=rec.fuso_horas
            )
            nsrs = [m["nsr"] for m in resultado.marcacoes]
            rec.write(
                {
                    "hash_arquivo": hashlib.sha256(bruto).hexdigest(),
                    "leiaute_detectado": resultado.leiaute,
                    "qtd_marcacoes": len(resultado.marcacoes),
                    "qtd_eventos": len(resultado.eventos),
                    "nsr_inicial": min(nsrs) if nsrs else 0,
                    "nsr_final": max(nsrs) if nsrs else 0,
                    "lacunas_nsr": rec._formata_lacunas(resultado.lacunas_nsr),
                    "log": rec._formata_log(resultado),
                    "state": "erro" if resultado.tem_erro else "analisado",
                }
            )
            rec._avisa_reimportacao()
        return True

    def _avisa_reimportacao(self):
        """Registra no chatter quando o mesmo arquivo já passou por aqui."""
        self.ensure_one()
        if not self.hash_arquivo:
            return
        anterior = self.search(
            [
                ("hash_arquivo", "=", self.hash_arquivo),
                ("id", "!=", self.id),
                ("state", "=", "importado"),
            ],
            limit=1,
        )
        if anterior:
            self.message_post(
                body=_(
                    "Este arquivo já foi importado em %s. A importação é "
                    "idempotente: os NSRs existentes serão ignorados."
                )
                % anterior.name
            )

    @staticmethod
    def _formata_lacunas(lacunas):
        if not lacunas:
            return ""
        return "\n".join(
            "NSR %d a %d ausentes (%d registros)." % (inicio, fim, fim - inicio + 1)
            for inicio, fim in lacunas
        )

    @staticmethod
    def _formata_log(resultado):
        if not resultado.ocorrencias:
            return ""
        return "\n".join(
            "Linha %s [%s]: %s" % (o.numero_linha, o.codigo, o.mensagem)
            for o in resultado.ocorrencias
        )

    def action_importar(self):
        """Grava as marcações novas, ignorando as que já existem (RP-08)."""
        for rec in self:
            if rec.state == "draft":
                rec.action_analisar()
            conteudo, _bruto = rec._conteudo_texto()
            leiaute = None if rec.leiaute == "auto" else rec.leiaute
            resultado = afd_parser.ler_afd(
                conteudo, leiaute=leiaute, fuso_horas=rec.fuso_horas
            )
            rec._importar_resultado(resultado)
        return True

    def _importar_resultado(self, resultado):
        self.ensure_one()
        Marcacao = self.env["l10n_br.hr.marcacao"]
        nsrs_arquivo = [m["nsr"] for m in resultado.marcacoes]
        existentes = set(
            Marcacao.search(
                [("rep_id", "=", self.rep_id.id), ("nsr", "in", nsrs_arquivo)]
            ).mapped("nsr")
        )
        indice = self.env["hr.employee"]._l10n_br_indice_documentos()
        # A origem é a natureza do registrador cadastrado; só o registro tipo 7
        # do Anexo V se auto-identifica como REP-P.
        origem = self.rep_id.tipo

        vals_list = []
        pendentes = 0
        for marcacao in resultado.marcacoes:
            if marcacao["nsr"] in existentes:
                continue
            employee = self.env["hr.employee"]._l10n_br_buscar_por_documento(
                cpf=marcacao.get("cpf"), pis=marcacao.get("pis"), indice=indice
            )
            if not employee:
                pendentes += 1
            vals = {
                "nsr": marcacao["nsr"],
                "rep_id": self.rep_id.id,
                "company_id": self.company_id.id,
                "employee_id": employee.id if employee else False,
                "cpf": marcacao.get("cpf") or "",
                "pis_pasep": marcacao.get("pis") or "",
                "datetime_marcacao": marcacao["datetime_marcacao"],
                "origem": ("rep_p" if marcacao["tipo_registro"] == "7" else origem),
                "afd_import_id": self.id,
            }
            if marcacao["tipo_registro"] == "7":
                vals.update(
                    {
                        "datetime_gravacao": marcacao.get("datetime_gravacao"),
                        "coletor": marcacao.get("coletor"),
                        "offline": marcacao.get("offline"),
                        "hash_registro": marcacao.get("hash_registro"),
                    }
                )
            vals_list.append(vals)

        criadas = Marcacao._criar_marcacoes(vals_list) if vals_list else Marcacao
        if nsrs_arquivo:
            self.rep_id._registrar_nsr_externo(max(nsrs_arquivo))

        self.write(
            {
                "qtd_importadas": len(criadas),
                "qtd_duplicadas": len(existentes),
                "qtd_pendentes": pendentes,
                "state": "erro" if resultado.tem_erro else "importado",
            }
        )
        self.message_post(
            body=_(
                "Importação concluída: %(novas)s marcações novas, "
                "%(dup)s já existentes, %(pend)s sem funcionário identificado."
            )
            % {
                "novas": len(criadas),
                "dup": len(existentes),
                "pend": pendentes,
            }
        )
        _logger.info(
            "AFD %s: %d marcações importadas, %d duplicadas, %d pendentes.",
            self.name,
            len(criadas),
            len(existentes),
            pendentes,
        )
        return criadas

    def action_ver_pendentes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Marcações sem funcionário"),
            "res_model": "l10n_br.hr.marcacao",
            "view_mode": "tree,form",
            "domain": [
                ("afd_import_id", "=", self.id),
                ("employee_id", "=", False),
            ],
        }

    def action_reconciliar_pendentes(self):
        """Tenta conciliar de novo, depois de cadastrar o CPF no funcionário.

        É o caminho normal quando o relógio já registrava alguém que ainda não
        estava no Odoo: em vez de reimportar o arquivo, reprocessa só o que
        ficou pendente.
        """
        indice = self.env["hr.employee"]._l10n_br_indice_documentos()
        total = 0
        for rec in self:
            pendentes = rec.marcacao_ids.filtered(lambda m: not m.employee_id)
            for marcacao in pendentes:
                employee = self.env["hr.employee"]._l10n_br_buscar_por_documento(
                    cpf=marcacao.cpf, pis=marcacao.pis_pasep, indice=indice
                )
                if employee:
                    marcacao._conciliar_funcionario(employee)
                    total += 1
            rec.qtd_pendentes = len(
                rec.marcacao_ids.filtered(lambda m: not m.employee_id)
            )
        if total:
            self.message_post(body=_("%s marcações conciliadas.") % total)
        return total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nova importação")) == _("Nova importação"):
                vals["name"] = vals.get("arquivo_nome") or _("Importação de AFD")
        return super().create(vals_list)
