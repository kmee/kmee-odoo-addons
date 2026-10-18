# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS1000(models.Model):
    _name = "l10n_br.esocial.s1000"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1000 - Informações do Empregador"

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

    def _get_event_type(self):
        return "S-1000"

    def _to_esociallib_dict(self):
        self.ensure_one()
        company = self.company_id

        if not company.l10n_br_esocial_class_trib_id:
            raise UserError(
                _(
                    "Empresa '%(name)s' não possui Classificação Tributária "
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
            "ini_valid": self.ini_valid,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }

        if self.fim_valid:
            data["fim_valid"] = self.fim_valid

        if self.operacao in ("inclusao", "alteracao"):
            data["class_trib"] = company.l10n_br_esocial_class_trib_id.codigo
            if company.l10n_br_esocial_ind_coop != "0":
                data["ind_coop"] = int(company.l10n_br_esocial_ind_coop)
            if company.l10n_br_esocial_ind_constr != "0":
                data["ind_constr"] = int(company.l10n_br_esocial_ind_constr)

        return data
