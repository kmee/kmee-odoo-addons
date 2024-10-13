# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DocumentLine(models.Model):
    _inherit = "l10n_br_fiscal.document.line"

    nfe40_med = fields.Many2one(
        related="product_id.nfe40_med",
        store=True,
    )
