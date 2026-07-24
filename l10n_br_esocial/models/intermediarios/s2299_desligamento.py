# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS2299(models.Model):
    _name = "l10n_br.esocial.s2299"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-2299 - Desligamento"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empregado",
        required=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contrato",
        required=True,
        ondelete="cascade",
    )
    dt_deslig = fields.Date(
        string="Data do Desligamento",
        required=True,
    )
    motivo_desligamento_id = fields.Many2one(
        "l10n_br.esocial.motivo.desligamento",
        string="Motivo Desligamento",
        required=True,
    )
    ind_pagto_api = fields.Selection(
        [
            ("S", "Sim"),
            ("N", "Não"),
        ],
        string="Aviso Prévio Indenizado",
        default="N",
    )
    dt_proj_fim_api = fields.Date(
        string="Data Projetada Fim Aviso Prévio",
    )

    def _get_event_type(self):
        return "S-2299"

    def _to_esociallib_dict(self):
        self.ensure_one()
        employee = self.employee_id

        cpf = employee.cnpj_cpf
        if not cpf:
            raise UserError(
                _("Empregado '%(name)s' não possui CPF configurado.")
                % {"name": employee.name}
            )
        cpf_limpo = "".join(c for c in cpf if c.isdigit())

        matricula = employee.l10n_br_esocial_matricula
        if not matricula:
            raise UserError(
                _("Empregado '%(name)s' não possui Matrícula eSocial.")
                % {"name": employee.name}
            )

        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
            "cpf_trab": cpf_limpo,
            "matricula": matricula,
            "mtv_deslig": self.motivo_desligamento_id.codigo,
            "dt_deslig": str(self.dt_deslig),
            "ind_pagto_api": self.ind_pagto_api or "N",
        }

        if self.ind_pagto_api == "S" and self.dt_proj_fim_api:
            data["dt_proj_fim_api"] = str(self.dt_proj_fim_api)

        return data
