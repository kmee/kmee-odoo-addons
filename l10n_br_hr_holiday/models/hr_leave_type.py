# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    l10n_br_category = fields.Selection(
        selection=[
            ("disease", "Doenca / Acidente"),
            ("maternity", "Maternidade / Paternidade"),
            ("family", "Evento Familiar (casamento, obito)"),
            ("civic", "Servico Civico / Militar / Eleitoral"),
            ("unjustified", "Falta Injustificada"),
            ("justified", "Falta Justificada"),
            ("other", "Outros"),
        ],
        string="Categoria CLT",
    )
    l10n_br_need_attachment = fields.Boolean(
        string="Exige Atestado/Comprovante",
        help="Exige anexo de atestado medico ou comprovante para validacao.",
    )
    l10n_br_payroll_discount = fields.Boolean(
        string="Desconta em Folha",
        help="Quando marcado, os dias de afastamento sao descontados do salario.",
    )
    l10n_br_discount_dsr = fields.Boolean(
        string="Desconta DSR",
        help="Quando marcado, faltas tambem descontam o Descanso Semanal Remunerado.",
    )
    l10n_br_days_limit = fields.Integer(
        string="Limite de Dias",
        help=("Limite de dias por periodo (12 meses). " "Zero = sem limite."),
    )
