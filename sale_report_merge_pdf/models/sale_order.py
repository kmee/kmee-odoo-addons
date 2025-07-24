import base64
import io
import logging

from pypdf import PdfReader, PdfWriter

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    merge_pdf = fields.Boolean(
        string="Print with Cover",
        default=True,
        help="Se marcado, o PDF da capa será incluído no relatório.",
    )

    def merge_with_cover_pdf(self, report_pdf):

        if not self.merge_pdf:
            return report_pdf

        cover_record = self.env["sale.order.cover.pdf"].get_active_cover()
        if not cover_record:
            return report_pdf

        try:
            writer = PdfWriter()

            capa_bytes = base64.b64decode(cover_record.cover_pdf)
            capa_reader = PdfReader(io.BytesIO(capa_bytes))
            for page in capa_reader.pages:
                writer.add_page(page)
            report_reader = PdfReader(io.BytesIO(report_pdf))
            for page in report_reader.pages:
                writer.add_page(page)

            output = io.BytesIO()
            writer.write(output)
            return output.getvalue()

        except Exception as e:
            _logger.error(f"Erro ao mesclar PDF da capa para {self.name}: {e}")
            return report_pdf
