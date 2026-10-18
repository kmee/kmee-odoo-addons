from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MonetaryIndex(models.Model):
    _name = "monetary.index"
    _description = "Monetary Index"
    _order = "name"

    name = fields.Char(required=True, help="Display name of the monetary index")
    code = fields.Char(
        required=True,
        help="Unique code for the index (e.g., selic, ipca, inpc, hicp, cpi)",
    )
    authority = fields.Char(
        help="Issuing authority or provider (e.g., BACEN, IBGE, OECD)",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        help="Country associated with this index",
    )
    description = fields.Text()
    active = fields.Boolean(default=True, help="If unchecked, the index is archived")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Company owning this index",
    )
    rate_ids = fields.One2many(
        comodel_name="monetary.index.rate",
        inverse_name="index_id",
        string="Rates",
        help="Historical rates for this index",
    )

    _sql_constraints = [
        (
            "code_company_unique",
            "UNIQUE(company_id, code)",
            "The code must be unique per company!",
        )
    ]

    @api.constrains("code", "company_id")
    def _check_code_unique(self):
        for record in self:
            if not record.code or not record.code.strip():
                raise ValidationError(_("Code cannot be empty!"))
            # Check case-insensitive uniqueness per company
            domain = [
                ("code", "=ilike", record.code),
                ("company_id", "=", record.company_id.id),
                ("id", "!=", record.id),
            ]
            duplicates = self.search(domain, limit=1)
            if duplicates:
                raise ValidationError(
                    _(
                        "The code '%(code)s' must be unique per company "
                        "(case-insensitive)!",
                    )
                    % {"code": record.code}
                )
