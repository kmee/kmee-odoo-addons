# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCoverPdf(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Cover = self.env["sale.order.cover.pdf"]
        self.Cover.search([]).unlink()

    def test_single_active_cover(self):
        self.Cover.create({"cover_pdf_filename": "a.pdf"})
        with self.assertRaises(ValidationError):
            self.Cover.create({"cover_pdf_filename": "b.pdf"})

    def test_inactive_cover_allowed(self):
        self.Cover.create({"cover_pdf_filename": "a.pdf"})
        other = self.Cover.create({"cover_pdf_filename": "b.pdf", "active": False})
        self.assertFalse(other.active)

    def test_get_active_cover_needs_pdf(self):
        self.assertFalse(self.Cover.get_active_cover())
        self.Cover.create({"cover_pdf_filename": "a.pdf"})
        self.assertFalse(self.Cover.get_active_cover())
        self.Cover.search([]).write({"cover_pdf": "JVBERi0="})
        self.assertTrue(self.Cover.get_active_cover())
