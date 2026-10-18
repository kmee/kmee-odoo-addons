from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MonetaryIndexRate(models.Model):
    _name = "monetary.index.rate"
    _description = "Monetary Index Rate"
    _order = "date desc"

    index_id = fields.Many2one(
        comodel_name="monetary.index",
        string="Index",
        required=True,
        ondelete="cascade",
        help="Associated monetary index",
    )
    date = fields.Date(
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
        default="manual",
        help="Origin of the rate data",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Company owning this rate",
    )
    note = fields.Char(help="Optional note or comment")

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
                raise ValidationError(_("Rate value cannot be less than -100%!"))
