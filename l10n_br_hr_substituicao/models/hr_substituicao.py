# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrSubstituicao(models.Model):
    _name = "hr.substituicao"
    _description = "Substituição de Funcionário"
    _order = "date_start desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Funcionário Titular",
        required=True,
    )
    substitute_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Funcionário Substituto",
        required=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Departamento",
        compute="_compute_department_id",
        store=True,
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        string="Cargo",
        related="employee_id.job_id",
        store=True,
        readonly=True,
    )
    leave_id = fields.Many2one(
        comodel_name="hr.leave",
        string="Afastamento",
        help="Licença/afastamento que gerou a substituição.",
    )
    date_start = fields.Date(
        string="Início",
        required=True,
    )
    date_end = fields.Date(
        string="Fim",
        required=True,
    )
    reason = fields.Text(string="Motivo")
    state = fields.Selection(
        selection=[
            ("draft", "Rascunho"),
            ("confirmed", "Confirmado"),
            ("done", "Encerrado"),
            ("cancelled", "Cancelado"),
        ],
        default="draft",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    @api.depends("employee_id")
    def _compute_department_id(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id

    @api.constrains("employee_id", "substitute_employee_id")
    def _check_different_employees(self):
        for rec in self:
            if rec.employee_id == rec.substitute_employee_id:
                raise ValidationError(
                    _("O titular e o substituto devem ser" " funcionários diferentes.")
                )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_end < rec.date_start:
                raise ValidationError(
                    _("A data de fim deve ser posterior à data de início.")
                )

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})
