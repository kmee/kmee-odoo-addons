# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CreditHistoryLine(models.Model):
    _name = "credit.history.line"
    _description = "Linha de Historico de Credito"
    _order = "year desc, month desc"

    analysis_id = fields.Many2one(
        comodel_name="credit.analysis",
        string="Consulta de Credito",
        required=True,
        ondelete="cascade",
    )
    month = fields.Selection(
        selection=[
            ("01", "Janeiro"),
            ("02", "Fevereiro"),
            ("03", "Marco"),
            ("04", "Abril"),
            ("05", "Maio"),
            ("06", "Junho"),
            ("07", "Julho"),
            ("08", "Agosto"),
            ("09", "Setembro"),
            ("10", "Outubro"),
            ("11", "Novembro"),
            ("12", "Dezembro"),
        ],
        string="Mes",
        required=True,
    )
    year = fields.Integer(
        string="Ano",
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    date = fields.Date(
        string="Data Referencia",
        compute="_compute_date",
        store=True,
    )
    value = fields.Monetary(
        string="Valor",
        currency_field="currency_id",
    )
    variation = fields.Float(
        string="Variacao (%)",
        compute="_compute_variation",
        store=True,
        digits=(5, 2),
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends("month", "year")
    def _compute_date(self):
        for record in self:
            if record.month and record.year:
                record.date = fields.Date.from_string(
                    f"{record.year}-{record.month}-01"
                )
            else:
                record.date = False

    @api.depends("value", "analysis_id.credit_history_ids")
    def _compute_variation(self):
        for record in self:
            # Find previous month
            prev_lines = record.analysis_id.credit_history_ids.filtered(
                lambda l: l.date and record.date and l.date < record.date
            ).sorted(key=lambda l: l.date, reverse=True)
            if prev_lines:
                prev_value = prev_lines[0].value
                if prev_value:
                    record.variation = (
                        (record.value - prev_value) / prev_value
                    ) * 100
                else:
                    record.variation = 0
            else:
                record.variation = 0

    def name_get(self):
        result = []
        month_labels = dict(self._fields["month"].selection)
        for record in self:
            month_name = month_labels.get(record.month, record.month)
            name = f"{month_name}/{record.year}"
            result.append((record.id, name))
        return result
