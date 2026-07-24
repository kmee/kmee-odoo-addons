from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialS2200(models.Model):
    _name = "l10n_br.esocial.s2200"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-2200 - Cadastramento Inicial / Admissão"

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

    def _get_event_type(self):
        return "S-2200"

    def _get_cpf_limpo(self, employee):
        cpf = employee.cnpj_cpf
        if not cpf:
            raise UserError(
                _("Empregado '%(name)s' não possui CPF configurado.")
                % {"name": employee.name}
            )
        return "".join(c for c in cpf if c.isdigit())

    def _to_esociallib_dict(self):
        self.ensure_one()
        employee = self.employee_id
        contract = self.contract_id

        cpf_limpo = self._get_cpf_limpo(employee)
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

        # Gender mapping
        gender_map = {"male": "M", "female": "F", "other": "M"}
        sexo = gender_map.get(employee.gender, "M")

        # Marital mapping to eSocial estCiv
        marital_map = {
            "single": 1,
            "married": 2,
            "divorced": 3,
            "widower": 5,
        }

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
            "cpf_trab": cpf_limpo,
            "nm_trab": employee.name,
            "sexo": sexo,
            "raca_cor": 1,  # Default: branca
            "grau_instr": "09",  # Default: ensino médio
            "dt_nascto": str(employee.birthday) if employee.birthday else "1990-01-01",
            "matricula": matricula,
            "tp_reg_trab": 1,  # CLT
            "tp_reg_prev": 1,  # RGPS
            "cod_categ": categoria.codigo,
        }

        est_civ = marital_map.get(employee.marital)
        if est_civ:
            data["est_civ"] = est_civ

        # CLT fields
        if contract.date_start:
            data["dt_adm"] = str(contract.date_start)
        data["nat_atividade"] = 1  # Normal

        # Union CNPJ (required for CLT)
        union_cnpj = getattr(contract, "union_cnpj", None)
        if union_cnpj:
            data["cnpj_sind_categ_prof"] = "".join(c for c in union_cnpj if c.isdigit())
        else:
            data["cnpj_sind_categ_prof"] = "00000000000000"

        # Salary
        if contract.wage:
            data["vr_sal_fx"] = str(contract.wage)
            data["und_sal_fixo"] = 5  # Mensal

        # CBO
        cbo = getattr(employee, "job_id", None)
        if cbo and hasattr(cbo, "l10n_br_cbo_id"):
            cbo_code = getattr(cbo.l10n_br_cbo_id, "code", None)
            if cbo_code:
                data["cod_cbo"] = cbo_code

        # Position name
        if employee.job_id:
            data["nm_cargo"] = employee.job_id.name

        return data
