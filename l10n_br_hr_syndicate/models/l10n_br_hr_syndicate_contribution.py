# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nBrHrSyndicateContribution(models.Model):
    _name = "l10n.br.hr.syndicate.contribution"
    _description = "Contribuição Sindical"
    _order = "year desc, month desc"

    partner_union_id = fields.Many2one(
        comodel_name="res.partner",
        string="Sindicato",
        domain=[("union_entity_code", "!=", False)],
        required=True,
    )
    year = fields.Integer(
        string="Ano",
        required=True,
    )
    month = fields.Selection(
        selection=[
            ("1", "Janeiro"),
            ("2", "Fevereiro"),
            ("3", "Março"),
            ("4", "Abril"),
            ("5", "Maio"),
            ("6", "Junho"),
            ("7", "Julho"),
            ("8", "Agosto"),
            ("9", "Setembro"),
            ("10", "Outubro"),
            ("11", "Novembro"),
            ("12", "Dezembro"),
        ],
        string="Mês de Desconto",
        required=True,
        help="Mês em que a contribuição é descontada do empregado.",
    )
    contribution_type = fields.Selection(
        selection=[
            ("assistencial", "Contribuição Assistencial"),
            ("confederativa", "Contribuição Confederativa"),
            ("sindical", "Contribuição Sindical (ex-imposto)"),
        ],
        string="Tipo",
        required=True,
        default="assistencial",
    )
    calc_method = fields.Selection(
        selection=[
            ("percent", "Percentual do Salário"),
            ("fixed", "Valor Fixo"),
            ("one_day", "Um Dia de Salário"),
        ],
        string="Método de Cálculo",
        required=True,
        default="percent",
    )
    percentage = fields.Float(
        string="Percentual (%)",
        help="Percentual sobre o salário bruto.",
    )
    fixed_amount = fields.Float(
        string="Valor Fixo",
        digits="Payroll",
    )
    active = fields.Boolean(default=True)
