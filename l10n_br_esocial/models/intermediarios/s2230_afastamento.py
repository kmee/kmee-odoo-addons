# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS2230(models.Model):
    _name = "l10n_br.esocial.s2230"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-2230 - Afastamento Temporário"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empregado",
        required=True,
        ondelete="cascade",
    )
    dt_ini_afast = fields.Date(
        string="Data Início Afastamento",
    )
    dt_term_afast = fields.Date(
        string="Data Término Afastamento",
    )
    cod_mot_afast = fields.Char(
        string="Código Motivo Afastamento",
        size=2,
        help="Código conforme Tabela 18 do eSocial.",
    )
    motivo_afastamento_id = fields.Many2one(
        "l10n_br.esocial.motivo.afastamento",
        string="Motivo Afastamento",
    )

    def _get_event_type(self):
        return "S-2230"

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

        if not self.dt_ini_afast and not self.dt_term_afast:
            raise UserError(_("Informe a data de início ou término do afastamento."))

        cod_mot = self.cod_mot_afast
        if not cod_mot and self.motivo_afastamento_id:
            cod_mot = self.motivo_afastamento_id.codigo

        if self.dt_ini_afast and not cod_mot:
            raise UserError(
                _(
                    "Código do motivo de afastamento é obrigatório "
                    "ao informar início do afastamento."
                )
            )

        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
            "cpf_trab": cpf_limpo,
        }

        if matricula:
            data["matricula"] = matricula

        if self.dt_ini_afast:
            data["dt_ini_afast"] = str(self.dt_ini_afast)
            data["cod_mot_afast"] = cod_mot

        if self.dt_term_afast:
            data["dt_term_afast"] = str(self.dt_term_afast)

        return data
