# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_br_document_import_ocr.models import ocr_engine


def _make_pdf(text):
    """PDF real (com camada de texto) gerado pelo próprio pymupdf."""
    doc = ocr_engine.fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    raw = doc.tobytes()
    doc.close()
    return raw


@tagged("post_install", "-at_install")
class TestOcrEngine(TransactionCase):
    def setUp(self):
        super().setUp()
        self.engine = self.env["l10n_br.ocr.engine"]
        self.company = self.env.company

    def test_sniff_mimetype(self):
        self.assertEqual(ocr_engine.sniff_mimetype(b"%PDF-1.7 x"), "application/pdf")
        self.assertEqual(ocr_engine.sniff_mimetype(b"\xff\xd8\xffabc"), "image/jpeg")
        self.assertIsNone(ocr_engine.sniff_mimetype(b"<?xml version='1.0'?>"))

    def test_pdf_com_texto_nativo_nao_usa_ocr(self):
        text = "NFS-e numero 123 valor total da nota R$ 100,00 " * 4
        raw = _make_pdf(text)
        result, method = self.engine.extract_text(
            raw, "application/pdf", company=self.company
        )
        self.assertEqual(method, "native_text")
        self.assertIn("NFS-e", result)

    def test_pdf_sem_texto_e_ocr_desligado(self):
        self.company.document_import_ocr_engine = "none"
        raw = _make_pdf("x")
        with self.assertRaises(UserError):
            self.engine.extract_text(raw, "application/pdf", company=self.company)

    def test_arquivo_gigante_e_recusado(self):
        raw = b"%PDF" + b"0" * (ocr_engine.MAX_FILE_BYTES + 1)
        with self.assertRaises(UserError):
            self.engine.extract_text(raw, "application/pdf", company=self.company)
