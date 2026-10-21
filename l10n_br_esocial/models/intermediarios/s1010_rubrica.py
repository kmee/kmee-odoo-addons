# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class ESocialS1010(models.Model):
    _name = "l10n_br.esocial.s1010"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1010 - Tabela de Rubricas"

    salary_rule_id = fields.Many2one(
        "hr.salary.rule",
        string="Regra Salarial",
        required=True,
        ondelete="cascade",
    )
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
        return "S-1010"

    def _to_esociallib_dict(self):
        self.ensure_one()
        rule = self.salary_rule_id

        if not rule.l10n_br_esocial_cod_rubr:
            raise UserError(f"Regra '{rule.name}' não possui Código Rubrica eSocial.")
        if not rule.l10n_br_esocial_nat_rubr_id:
            raise UserError(
                f"Regra '{rule.name}' não possui Natureza de Rubrica eSocial."
            )
        if not rule.l10n_br_esocial_tp_rubr:
            raise UserError(f"Regra '{rule.name}' não possui Tipo de Rubrica eSocial.")

        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "operacao": self.operacao,
            "cod_rubr": rule.l10n_br_esocial_cod_rubr,
            "ide_tab_rubr": rule.l10n_br_esocial_ide_tab_rubr or "1",
            "ini_valid": self.ini_valid,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }

        if self.fim_valid:
            data["fim_valid"] = self.fim_valid

        # dadosRubrica (required for inclusao/alteracao)
        if self.operacao in ("inclusao", "alteracao"):
            data.update(
                {
                    "dsc_rubr": rule.name,
                    "nat_rubr": int(rule.l10n_br_esocial_nat_rubr_id.codigo),
                    "tp_rubr": int(rule.l10n_br_esocial_tp_rubr),
                    "cod_inc_cp": rule.l10n_br_esocial_cod_inc_cp or "00",
                    "cod_inc_irrf": int(rule.l10n_br_esocial_cod_inc_irrf or "0"),
                    "cod_inc_fgts": rule.l10n_br_esocial_cod_inc_fgts or "00",
                }
            )

        return data
