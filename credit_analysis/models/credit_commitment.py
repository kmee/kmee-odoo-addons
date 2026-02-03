# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CreditCommitmentLine(models.Model):
    _name = "credit.commitment.line"
    _description = "Linha de Comprometimento Futuro"
    _order = "year, month"

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
    qtd_titulos = fields.Integer(
        string="Quantidade de Titulos",
        default=0,
    )
    value = fields.Monetary(
        string="Valor",
        currency_field="currency_id",
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

    def name_get(self):
        result = []
        month_labels = dict(self._fields["month"].selection)
        for record in self:
            month_name = month_labels.get(record.month, record.month)
            name = f"{month_name}/{record.year}"
            result.append((record.id, name))
        return result
