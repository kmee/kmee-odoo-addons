from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MonetaryUpdateIndexRate(models.Model):
    _name = "monetary.update.index.rate"
    _description = "Monetary Update Index Rate"
    _order = "date desc"

    index_id = fields.Many2one(
        comodel_name="monetary.update.index",
        string="Index",
        required=True,
        ondelete="cascade",
        help="Associated monetary index",
    )
    date = fields.Date(
        string="Date",
        required=True,
        help="Competence date (use 1st day of month for monthly series)",
    )
    value = fields.Float(
        string="Value (%)",
        required=True,
        digits=(16, 6),
        help="Rate value as percentage for the period",
    )
    source = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("api", "API"),
        ],
        string="Source",
        default="manual",
        help="Origin of the rate data",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Company owning this rate",
    )
    note = fields.Char(string="Note", help="Optional note or comment")

    _sql_constraints = [
        (
            "index_date_unique",
            "UNIQUE(index_id, date)",
            "There can only be one rate per index and date!",
        )
    ]

    @api.constrains("value")
    def _check_value(self):
        for record in self:
            if record.value < -100.0:
                raise ValidationError("Rate value cannot be less than -100%!")
