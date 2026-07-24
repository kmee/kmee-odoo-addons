# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from erpbrasil.base.fiscal import cnpj_cpf

from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.constrains("employee_id", "date_from", "date_to", "struct_id", "state")
    def _check_payslip_duplicate_period(self):
        """Impede holerites com período sobreposto para o mesmo
        empregado/estrutura.

        A verificação anterior comparava apenas datas exatas, permitindo que
        dois holerites do mesmo mês/estrutura (ex.: 01-15 e 01-31) coexistissem.
        Agora detecta qualquer sobreposição de intervalo
        (``date_from <= other.date_to AND date_to >= other.date_from``).
        """
        for rec in self:
            if rec.state == "cancel":
                continue
            if not rec.date_from or not rec.date_to:
                continue
            domain = [
                ("employee_id", "=", rec.employee_id.id),
                ("struct_id", "=", rec.struct_id.id),
                ("state", "!=", "cancel"),
                ("id", "!=", rec.id),
                ("date_from", "<=", rec.date_to),
                ("date_to", ">=", rec.date_from),
            ]
            other = self.search(domain, limit=1)
            if other:
                raise ValidationError(
                    _(
                        "Já existe um holerite para o empregado "
                        "'%(employee)s' com período sobreposto "
                        "(%(other_from)s a %(other_to)s) à faixa "
                        "%(date_from)s a %(date_to)s, na mesma estrutura "
                        "salarial.",
                        employee=rec.employee_id.name,
                        other_from=other.date_from,
                        other_to=other.date_to,
                        date_from=rec.date_from,
                        date_to=rec.date_to,
                    )
                )

    @api.constrains("date_from", "date_to")
    def _check_payslip_dates(self):
        """Validate payslip date range."""
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(
                    _(
                        "A data inicial (%(date_from)s) não pode ser "
                        "posterior à data final (%(date_to)s).",
                        date_from=rec.date_from,
                        date_to=rec.date_to,
                    )
                )

    def action_payslip_done(self):
        """Validate payslip consistency before confirming."""
        for rec in self:
            # CPF obrigatório
            cpf = rec.employee_id.cnpj_cpf if rec.employee_id else False
            if rec.employee_id and not cpf:
                raise ValidationError(
                    _(
                        "O empregado '%(employee)s' não possui CPF "
                        "cadastrado. O CPF é obrigatório para confirmar "
                        "a folha.",
                        employee=rec.employee_id.name,
                    )
                )
            # CPF com dígitos verificadores válidos
            if cpf and not cnpj_cpf.validar_cpf(cpf):
                raise ValidationError(
                    _(
                        "O CPF '%(cpf)s' do empregado '%(employee)s' é "
                        "inválido (dígitos verificadores incorretos).",
                        cpf=cpf,
                        employee=rec.employee_id.name,
                    )
                )
            if not rec.line_ids:
                raise ValidationError(
                    _(
                        "O holerite de '%(employee)s' não possui linhas "
                        "calculadas. Compute a folha antes de confirmar.",
                        employee=rec.employee_id.name,
                    )
                )
            net_lines = rec.line_ids.filtered(lambda line: line.code == "NET")
            if not net_lines:
                raise ValidationError(
                    _(
                        "O holerite de '%(employee)s' não possui linha "
                        "de líquido (NET). Verifique a estrutura salarial.",
                        employee=rec.employee_id.name,
                    )
                )
        return super().action_payslip_done()
