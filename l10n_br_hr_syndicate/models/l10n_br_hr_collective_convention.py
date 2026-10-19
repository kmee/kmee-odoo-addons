# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class L10nBrHrCollectiveConvention(models.Model):
    _name = "l10n.br.hr.collective.convention"
    _description = "Convenção Coletiva de Trabalho"
    _order = "date_start desc"

    name = fields.Char(required=True)
    partner_union_id = fields.Many2one(
        comodel_name="res.partner",
        string="Sindicato",
        domain=[("union_entity_code", "!=", False)],
        required=True,
    )
    date_start = fields.Date(
        string="Vigência Início",
        required=True,
    )
    date_end = fields.Date(
        string="Vigência Fim",
        required=True,
    )
    dissidio_month = fields.Selection(
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
        string="Mês do Dissídio (Data-Base)",
    )
    wage_floor = fields.Float(
        string="Piso Salarial",
        digits="Payroll",
        help="Piso salarial definido pela convenção coletiva.",
    )
    wage_floor_job_ids = fields.One2many(
        comodel_name="l10n.br.hr.convention.wage.floor",
        inverse_name="convention_id",
        string="Pisos por Cargo",
    )
    contribution_employee_pct = fields.Float(
        string="Contribuição Empregado (%)",
        help="Percentual de contribuição assistencial do empregado.",
    )
    contribution_employer_pct = fields.Float(
        string="Contribuição Patronal (%)",
        help="Percentual de contribuição patronal ao sindicato.",
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Observações")

    @api.depends("partner_union_id", "date_start")
    def _compute_display_name(self):
        for rec in self:
            if rec.partner_union_id and rec.date_start:
                rec.display_name = (
                    f"{rec.partner_union_id.name} - "
                    f"{rec.date_start.year}/{rec.date_start.year + 1}"
                )
            else:
                rec.display_name = rec.name


class L10nBrHrConventionWageFloor(models.Model):
    _name = "l10n.br.hr.convention.wage.floor"
    _description = "Piso Salarial por Cargo"

    convention_id = fields.Many2one(
        comodel_name="l10n.br.hr.collective.convention",
        required=True,
        ondelete="cascade",
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        string="Cargo",
        required=True,
    )
    wage_floor = fields.Float(
        string="Piso Salarial",
        digits="Payroll",
        required=True,
    )
