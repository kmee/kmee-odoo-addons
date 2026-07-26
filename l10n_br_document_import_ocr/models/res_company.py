# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    document_import_ocr_engine = fields.Selection(
        selection=[
            ("none", "Somente texto nativo do PDF"),
            ("tesseract", "Tesseract (local, CPU)"),
            ("rapidocr", "RapidOCR / PP-OCR (ONNX)"),
            ("http", "Backend HTTP (VLM, OpenAI-compatible)"),
        ],
        string="Engine de OCR",
        default="tesseract",
    )
    document_import_destination = fields.Selection(
        selection=[
            ("fiscal", "Somente Documento Fiscal"),
            ("move", "Documento Fiscal + Fatura"),
        ],
        string="Destino da importação",
        default="move",
    )
    document_import_default_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Operação fiscal padrão (serviços tomados)",
        domain=[("fiscal_operation_type", "=", "in")],
    )
