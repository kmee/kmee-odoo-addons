from odoo import fields, models


class MonetaryIndex(models.Model):
    _inherit = "monetary.index"

    bcb_sgs_code = fields.Char(
        string="SGS Series (BCB)",
        help="Series code in the Time Series Management System (SGS) of the "
        "Banco Central do Brasil (e.g. 433 IPCA, 188 INPC, 189 IGP-M, "
        "4390 SELIC). With the code set, the rates are fetched from the "
        "Banco Central API.",
    )
