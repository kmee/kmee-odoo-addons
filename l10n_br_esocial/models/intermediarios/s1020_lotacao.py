# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS1020(models.Model):
    _name = "l10n_br.esocial.s1020"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1020 - Tabela de Lotações Tributárias"

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
    fpas = fields.Char(
        string="FPAS",
        size=3,
        help="Código FPAS (Fundo de Previdência e Assistência Social).",
    )
    cod_tercs = fields.Char(
        string="Código Terceiros",
        size=4,
        help="Código de terceiros (SESC, SENAI, etc.).",
    )

    def _get_event_type(self):
        return "S-1020"

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
            data["tp_lotacao"] = company.l10n_br_esocial_lotacao_id.codigo
            data["fpas"] = self.fpas or "515"
            data["cod_tercs"] = self.cod_tercs or "0000"

        return data
