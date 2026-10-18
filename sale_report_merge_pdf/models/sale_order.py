import base64
import io
import logging

from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from odoo import fields, models
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    merge_pdf = fields.Boolean(
        string="Print with Cover",
        default=True,
        help="Se marcado, o PDF da capa será incluído no relatório.",
    )

    def merge_with_cover_pdf(self, report_pdf):
        writer = PdfWriter()

        if self.merge_pdf:
            cover_record = self.env["sale.order.cover.pdf"].get_active_cover()
            if cover_record:
                try:
                    capa_bytes = base64.b64decode(cover_record.cover_pdf)
                    capa_reader = PdfReader(io.BytesIO(capa_bytes))
                    for page in capa_reader.pages:
                        writer.add_page(page)
                except Exception as e:
                    _logger.error(f"[{self.name}] Erro ao adicionar capa: {e}")

        try:
            report_reader = PdfReader(io.BytesIO(report_pdf))
            for page in report_reader.pages:
                writer.add_page(page)
        except Exception as e:
            _logger.error(f"[{self.name}] Erro ao adicionar relatório principal: {e}")
            return report_pdf

        try:
            company = self.env.company
            if company.terms_type == "html":
                default_terms_text = html2plaintext(company.invoice_terms_html)

            if default_terms_text:
                soup = BeautifulSoup(default_terms_text, "html.parser")
                default_terms_text = soup.get_text().strip()

                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # Margens e configurações de texto
                left_margin = 20 * mm
                right_margin = 20 * mm
                top_margin = 30 * mm
                bottom_margin = 20 * mm

                title_font = "Helvetica-Bold"
                title_size = 16
                body_font = "Helvetica"
                body_size = 10
                line_height = body_size * 1.2

                # Título
                c.setFont(title_font, title_size)
                c.drawString(left_margin, height - top_margin, "Termos e Condições")

                # Texto
                c.setFont(body_font, body_size)
                max_width = width - left_margin - right_margin

                # Quebra de texto automática considerando a largura da página
                wrapped_lines = simpleSplit(
                    default_terms_text, body_font, body_size, max_width
                )

                y = height - top_margin - 10 * mm

                for line in wrapped_lines:
                    if y <= bottom_margin:
                        c.showPage()
                        c.setFont(body_font, body_size)
                        y = height - top_margin
                    c.drawString(left_margin, y, line)
                    y -= line_height

                c.showPage()
                c.save()

                buffer.seek(0)
                terms_generated = PdfReader(buffer)
                for page in terms_generated.pages:
                    writer.add_page(page)

        except Exception as e:
            _logger.error(
                f"[{self.name}] Erro ao adicionar termos padrão do sistema: {e}"
            )

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
