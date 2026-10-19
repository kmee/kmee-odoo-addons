# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from erpbrasil.base.misc import punctuation_rm

from odoo import _, fields, models
from odoo.exceptions import UserError

from . import afd_parser


class L10nBrHrRep(models.Model):
    _inherit = "l10n_br.hr.rep"

    def _cabecalho_afd(self, date_from, date_to, momento_geracao=None):
        """Monta o registro tipo 1 a partir do cadastro do REP."""
        self.ensure_one()
        empresa = self.company_id
        momento = momento_geracao or fields.Datetime.now()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        return {
            "tipo_identificador_empregador": self.tipo_inscricao,
            "cnpj_cpf_empregador": punctuation_rm(self.cnpj_cpf or ""),
            "cno_caepf": punctuation_rm(self.caepf_cno or ""),
            "razao_social": (empresa.name or "")[:150],
            "identificador_rep": punctuation_rm(self._identificador_afd()),
            "data_inicial": fields.Date.to_string(date_from),
            "data_final": fields.Date.to_string(date_to),
            "data_hora_geracao": afd_parser.formata_datetime(momento),
            "tipo_identificador_fabricante": self.fabricante_tipo_inscricao or "1",
            "cnpj_cpf_fabricante": punctuation_rm(self.fabricante_cnpj_cpf or ""),
            "modelo": (self.modelo or "")[:30],
        }

    def _marcacoes_afd(self, date_from, date_to):
        """Marcações do período, ordenadas por NSR como exige o Anexo V."""
        self.ensure_one()
        marcacoes = self.env["l10n_br.hr.marcacao"].search(
            [
                ("rep_id", "=", self.id),
                ("date_marcacao", ">=", date_from),
                ("date_marcacao", "<=", date_to),
            ],
            order="nsr asc",
        )
        tipo_registro = "7" if self.tipo == "rep_p" else "3"
        return [
            {
                "nsr": marcacao.nsr,
                "tipo_registro": tipo_registro,
                "datetime_marcacao": marcacao.datetime_marcacao,
                "datetime_gravacao": marcacao.datetime_gravacao,
                "cpf": punctuation_rm(
                    marcacao.cpf or marcacao.employee_id.sudo().cpf or ""
                ),
                "coletor": marcacao.coletor,
                "offline": marcacao.offline,
                "hash_registro": marcacao.hash_registro,
            }
            for marcacao in marcacoes
        ]

    def gerar_afd(self, date_from, date_to, fuso_horas=-3.0):
        """Gera o AFD do período (RP-28).

        Returns:
            Tupla ``(nome_do_arquivo, conteudo_texto)``.
        """
        self.ensure_one()
        marcacoes = self._marcacoes_afd(date_from, date_to)
        if not marcacoes:
            raise UserError(
                _("Não há marcações deste REP entre %(inicio)s e %(fim)s.")
                % {"inicio": date_from, "fim": date_to}
            )
        conteudo = afd_parser.gerar_afd(
            self._cabecalho_afd(date_from, date_to),
            marcacoes,
            fuso_horas=fuso_horas,
        )
        nome = afd_parser.nome_arquivo_afd(
            self.tipo,
            punctuation_rm(self._identificador_afd()),
            punctuation_rm(self.cnpj_cpf or ""),
        )
        return nome, conteudo
