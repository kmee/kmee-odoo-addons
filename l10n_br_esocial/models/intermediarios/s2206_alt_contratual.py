from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS2206(models.Model):
    _name = "l10n_br.esocial.s2206"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-2206 - Alteração de Contrato de Trabalho"

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
    dt_alteracao = fields.Date(
        string="Data da Alteração",
        required=True,
    )
    dsc_alt = fields.Char(
        string="Descrição da Alteração",
        size=150,
    )

    def _get_event_type(self):
        return "S-2206"

    def _to_esociallib_dict(self):
        self.ensure_one()
        employee = self.employee_id
        contract = self.contract_id

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

        categoria = employee.l10n_br_esocial_categoria_id
        if not categoria:
            raise UserError(
                _("Empregado '%(name)s' não possui Categoria Trabalhador eSocial.")
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
            "dt_alteracao": str(self.dt_alteracao),
            "tp_reg_prev": 1,  # RGPS
            "tp_reg_trab": 1,  # CLT
            "nat_atividade": 1,  # Normal
            "cod_categ": categoria.codigo,
        }

        if self.dsc_alt:
            data["dsc_alt"] = self.dsc_alt

        # Union CNPJ (required for CLT)
        union_cnpj = getattr(contract, "union_cnpj", None)
        if union_cnpj:
            data["cnpj_sind_categ_prof"] = "".join(c for c in union_cnpj if c.isdigit())
        else:
            data["cnpj_sind_categ_prof"] = "00000000000000"

        if contract.wage:
            data["vr_sal_fx"] = str(contract.wage)
            data["und_sal_fixo"] = 5  # Mensal

        if employee.job_id:
            data["nm_cargo"] = employee.job_id.name

        return data
