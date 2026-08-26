# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import io
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None
    _logger.info("pymupdf (fitz) not installed; PDF import will be unavailable.")

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

# Abaixo desta média de caracteres por página o PDF é tratado como
# escaneado (raster) e vai para o OCR.
MIN_NATIVE_CHARS_PER_PAGE = 80
# Limite de páginas rasterizadas por documento (performance no onchange).
MAX_OCR_PAGES = 2
OCR_DPI = 300

PDF_MAGIC = b"%PDF"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def sniff_mimetype(raw):
    head = raw.lstrip()[:8] if raw else b""
    if head.startswith(PDF_MAGIC):
        return "application/pdf"
    if raw.startswith(PNG_MAGIC):
        return "image/png"
    if raw.startswith(JPEG_MAGIC):
        return "image/jpeg"
    return None


class OcrEngine(models.AbstractModel):
    _name = "l10n_br.ocr.engine"
    _description = "Extração de texto de PDF/imagem (nativo + OCR)"

    def extract_text(self, raw, mimetype, company=None):
        """Extrai o texto de um PDF/imagem.

        :return: (text, method) onde method é "native_text" ou "ocr".
        """
        company = company or self.env.company
        if mimetype == "application/pdf":
            text = self._pdf_native_text(raw)
            if text is not None:
                return text, "native_text"
            images = self._pdf_to_images(raw)
        else:
            images = [raw]
        engine = company.document_import_ocr_engine or "none"
        if engine == "none":
            raise UserError(
                _(
                    "O documento não tem camada de texto e o OCR está "
                    "desativado. Ative um engine de OCR nas configurações "
                    "fiscais da empresa."
                )
            )
        handler = getattr(self, "_ocr_%s" % engine, None)
        if handler is None:
            raise UserError(_("Engine de OCR desconhecido: %s") % engine)
        return handler(images, company), "ocr"

    def _pdf_native_text(self, raw):
        """Texto da camada nativa do PDF; None quando o PDF é escaneado."""
        if fitz is None:
            raise UserError(_("A biblioteca pymupdf não está instalada no servidor."))
        with fitz.open(stream=raw, filetype="pdf") as doc:
            pages = [page.get_text() for page in doc]
        text = "\n".join(pages)
        if pages and len(text) / len(pages) >= MIN_NATIVE_CHARS_PER_PAGE:
            return text
        return None

    def _pdf_to_images(self, raw):
        """Rasteriza as primeiras páginas do PDF (PNG bytes)."""
        images = []
        with fitz.open(stream=raw, filetype="pdf") as doc:
            for page in list(doc)[:MAX_OCR_PAGES]:
                pix = page.get_pixmap(dpi=OCR_DPI)
                images.append(pix.tobytes("png"))
        return images

    def _ocr_tesseract(self, images, company):
        if pytesseract is None or Image is None:
            raise UserError(
                _(
                    "O engine Tesseract está configurado mas o pacote "
                    "pytesseract (e/ou Pillow) não está instalado no "
                    "servidor. Instale-os ou mude o engine nas "
                    "configurações."
                )
            )
        texts = []
        for image_bytes in images:
            image = Image.open(io.BytesIO(image_bytes))
            texts.append(pytesseract.image_to_string(image, lang="por"))
        return "\n".join(texts)

    def _ocr_rapidocr(self, images, company):
        raise UserError(_("O engine RapidOCR ainda não está disponível nesta versão."))

    def _ocr_http(self, images, company):
        raise UserError(
            _("O engine HTTP (VLM) ainda não está disponível nesta " "versão.")
        )
