# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.constrains("employee_id", "date_from", "date_to", "struct_id", "state")
    def _check_payslip_duplicate_period(self):
        """Prevent duplicate payslips for same employee/period/structure."""
        for rec in self:
            if rec.state == "cancel":
                continue
            domain = [
                ("employee_id", "=", rec.employee_id.id),
                ("date_from", "=", rec.date_from),
                ("date_to", "=", rec.date_to),
                ("struct_id", "=", rec.struct_id.id),
                ("state", "!=", "cancel"),
                ("id", "!=", rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _(
                        "Já existe um holerite para o empregado "
                        "'%(employee)s' no período %(date_from)s a "
                        "%(date_to)s com a mesma estrutura salarial.",
                        employee=rec.employee_id.name,
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
            if rec.employee_id and not rec.employee_id.cnpj_cpf:
                raise ValidationError(
                    _(
                        "O empregado '%(employee)s' não possui CPF "
                        "cadastrado. O CPF é obrigatório para confirmar "
                        "a folha.",
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
