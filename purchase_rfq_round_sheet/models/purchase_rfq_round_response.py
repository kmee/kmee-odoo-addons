# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundResponse(models.Model):
    _inherit = "purchase.rfq.round.response"

    source = fields.Selection(
        selection_add=[("import", "Spreadsheet")],
        ondelete={"import": "set default"},
    )
    file_name = fields.Char()
    raw_values = fields.Json(help="Valores da linha como vieram na planilha.")
