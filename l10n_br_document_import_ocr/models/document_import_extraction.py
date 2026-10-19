# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import base64
import hashlib
import logging
import time

from odoo import fields, models

from .ocr_engine import sniff_mimetype

_logger = logging.getLogger(__name__)


class DocumentImportExtraction(models.Model):
    _name = "l10n_br.document.import.extraction"
    _description = "Extração de documento importado (cache e auditoria)"
    _order = "create_date desc"

    name = fields.Char(string="Arquivo")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
    )
    file_checksum = fields.Char(index=True, readonly=True)
    mimetype = fields.Char(readonly=True)
    raw_text = fields.Text(string="Texto extraído", readonly=True)
    structured_data = fields.Json(readonly=True)
    field_confidence = fields.Json(readonly=True)
    extraction_method = fields.Selection(
        selection=[
            ("native_text", "Texto nativo do PDF"),
            ("ocr", "OCR"),
        ],
        readonly=True,
    )
    structuring_method = fields.Char(readonly=True)
    state = fields.Selection(
        selection=[
            ("done", "Concluída"),
            ("failed", "Falhou"),
        ],
        readonly=True,
    )
    error_message = fields.Text(readonly=True)
    duration = fields.Float(string="Duração (s)", readonly=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Fornecedor detectado", readonly=True
    )
    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Documento criado",
        readonly=True,
    )

    def get_or_create_for_file(self, file_b64, filename=None, company=None):
        """Retorna a extração do arquivo, rodando o pipeline só em cache miss."""
        company = company or self.env.company
        raw = base64.b64decode(file_b64)
        checksum = hashlib.sha256(raw).hexdigest()
        extraction = self.search(
            [
                ("file_checksum", "=", checksum),
                ("company_id", "=", company.id),
                ("state", "=", "done"),
            ],
            limit=1,
        )
        if extraction:
            return extraction
        return self._run_pipeline(raw, checksum, filename, company)

    def _run_pipeline(self, raw, checksum, filename, company):
        started = time.monotonic()
        mimetype = sniff_mimetype(raw)
        text, method = self.env["l10n_br.ocr.engine"].extract_text(
            raw, mimetype, company=company
        )
        data, confidence, structuring = self.env["l10n_br.document.extractor"].extract(
            text, company
        )
        return self.create(
            {
                "name": filename or "documento",
                "company_id": company.id,
                "file_checksum": checksum,
                "mimetype": mimetype,
                "raw_text": text,
                "structured_data": data,
                "field_confidence": confidence,
                "extraction_method": method,
                "structuring_method": structuring,
                "state": "done",
                "duration": time.monotonic() - started,
            }
        )
