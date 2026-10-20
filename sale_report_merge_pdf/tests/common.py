# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from odoo.tests.common import TransactionCase


def make_pdf(pages, label="page"):
    """Return the bytes of a real PDF with the given number of pages."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for number in range(pages):
        pdf.drawString(100, 700, "%s %s" % (label, number + 1))
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def page_texts(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return [page.extract_text() for page in reader.pages]


class CoverPdfCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Cover = cls.env["sale.order.cover.pdf"]
        cls.Cover.with_context(active_test=False).search([]).unlink()
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create({"name": "Product"})
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [(0, 0, {"product_id": cls.product.id})],
            }
        )

    @classmethod
    def make_cover(cls, pages=1, **vals):
        values = {
            "cover_pdf": base64.b64encode(make_pdf(pages, "cover")),
            "cover_pdf_filename": "cover.pdf",
        }
        values.update(vals)
        return cls.Cover.create(values)
