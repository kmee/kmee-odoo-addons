# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    document_import_ocr_engine = fields.Selection(
        related="company_id.document_import_ocr_engine",
        readonly=False,
    )
    document_import_destination = fields.Selection(
        related="company_id.document_import_destination",
        readonly=False,
    )
    document_import_default_operation_id = fields.Many2one(
        related="company_id.document_import_default_operation_id",
        readonly=False,
    )
