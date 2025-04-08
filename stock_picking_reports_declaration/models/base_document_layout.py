# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):

    _inherit = "base.document.layout"

    declaration_receipt = fields.Html(
        related="company_id.declaration_receipt", readonly=False
    )
