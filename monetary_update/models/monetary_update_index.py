from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MonetaryUpdateIndex(models.Model):
    _name = "monetary.update.index"
    _description = "Monetary Update Index"
    _order = "name"

    name = fields.Char(
        string="Name", required=True, help="Display name of the monetary index"
    )
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for the index (e.g., selic, ipca, inpc, hicp, cpi)",
    )
    authority = fields.Char(
        string="Authority",
        help="Issuing authority or provider (e.g., BACEN, IBGE, OECD)",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Country",
        help="Country associated with this index",
    )
    description = fields.Text(
        string="Description", help="Detailed description of the index"
    )
    active = fields.Boolean(
        string="Active", default=True, help="If unchecked, the index is archived"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Company owning this index",
    )
    rate_ids = fields.One2many(
        comodel_name="monetary.update.index.rate",
        inverse_name="index_id",
        string="Rates",
        help="Historical rates for this index",
    )

    _sql_constraints = [
        (
            "code_company_unique",
            "UNIQUE(company_id, LOWER(code))",
            "The code must be unique per company!",
        )
    ]

    @api.constrains("code")
    def _check_code(self):
        for record in self:
            if not record.code or not record.code.strip():
                raise ValidationError("Code cannot be empty!")
