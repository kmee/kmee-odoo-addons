# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import CoverPdfCase, make_pdf, page_texts

LOGGER = "odoo.addons.sale_report_merge_pdf.models.sale_order"
PYPDF = "pypdf._reader"
REPORT_LOGGER = "odoo.addons.sale_report_merge_pdf.models.ir_actions_report"


@tagged("post_install", "-at_install")
class TestMergeWithCover(CoverPdfCase):
    def setUp(self):
        super().setUp()
        self.report = make_pdf(2, "report")
        self.company = self.env.company

    def test_cover_pages_come_before_report_pages(self):
        """
        Given an active cover of 1 page and a report of 2 pages
        When the order merges them
        Then the result has the cover first and the report pages after it
        """
        self.make_cover(pages=1)
        merged = self.order.merge_with_cover_pdf(self.report)
        texts = page_texts(merged)
        self.assertEqual(len(texts), 3)
        self.assertIn("cover 1", texts[0])
        self.assertIn("report 1", texts[1])
        self.assertIn("report 2", texts[2])

    def test_multi_page_cover_is_fully_included(self):
        """
        Given a cover with 3 pages
        When the order merges it with a 2 page report
        Then 5 pages are produced
        """
        self.make_cover(pages=3)
        self.assertEqual(
            len(page_texts(self.order.merge_with_cover_pdf(self.report))), 5
        )

    def test_no_cover_keeps_only_the_report_pages(self):
        """
        Given no active cover
        When the order merges
        Then only the report pages remain
        """
        texts = page_texts(self.order.merge_with_cover_pdf(self.report))
        self.assertEqual(len(texts), 2)
        self.assertIn("report 1", texts[0])

    def test_order_with_merge_disabled_gets_no_cover(self):
        """
        Given an active cover and an order with Print with Cover unchecked
        When the order merges
        Then the cover is not added
        """
        self.make_cover()
        self.order.merge_pdf = False
        texts = page_texts(self.order.merge_with_cover_pdf(self.report))
        self.assertEqual(len(texts), 2)
        self.assertNotIn("cover", " ".join(texts))

    def test_company_terms_are_appended_as_last_page(self):
        """
        Given a company with terms and conditions published as HTML
        When the order merges the cover and report
        Then a Terms and Conditions page with the text closes the document
        """
        self.make_cover()
        self.company.write(
            {"terms_type": "html", "invoice_terms_html": "<p>Payment in 30 days</p>"}
        )
        texts = page_texts(self.order.merge_with_cover_pdf(self.report))
        self.assertEqual(len(texts), 4)
        self.assertIn("Payment in 30 days", texts[-1])
        self.assertIn("Termos", texts[-1])

    def test_long_company_terms_span_several_pages(self):
        """
        Given company terms too long for a single page
        When the order merges the report with the terms
        Then the terms are written over more than one page
        """
        self.company.write(
            {
                "terms_type": "html",
                "invoice_terms_html": "<p>%s</p>" % ("clause text " * 1500),
            }
        )
        texts = page_texts(self.order.merge_with_cover_pdf(self.report))
        self.assertGreater(len(texts), 4)
        self.assertIn("clause text", texts[-1])

    def test_plain_terms_do_not_break_the_merge(self):
        """
        Given a company whose terms are a plain note (not HTML)
        When the order merges the cover and report
        Then the merge succeeds without any error logged
        """
        self.make_cover()
        self.company.terms_type = "plain"
        with self.assertNoLogs(LOGGER, level="ERROR"):
            merged = self.order.merge_with_cover_pdf(self.report)
        self.assertEqual(len(page_texts(merged)), 3)

    def test_invalid_report_bytes_return_original_content(self):
        """
        Given report content that is not a PDF
        When the order merges it
        Then the original content is returned untouched
        """
        self.make_cover()
        with mute_logger(LOGGER, PYPDF):
            merged = self.order.merge_with_cover_pdf(b"<html>not a pdf</html>")
        self.assertEqual(merged, b"<html>not a pdf</html>")

    def test_corrupted_cover_is_skipped(self):
        """
        Given an active cover whose file is not a valid PDF
        When the order merges
        Then the report pages are still produced, without the cover
        """
        self.make_cover(cover_pdf="Tm90IGEgcGRm")
        with mute_logger(LOGGER, PYPDF):
            texts = page_texts(self.order.merge_with_cover_pdf(self.report))
        self.assertEqual(len(texts), 2)


@tagged("post_install", "-at_install")
class TestApplyMerge(CoverPdfCase):
    def setUp(self):
        super().setUp()
        self.report = make_pdf(1, "report")
        self.Report = self.env["ir.actions.report"]

    def test_apply_merge_adds_cover(self):
        """
        Given an active cover and an order that prints with cover
        When the report layer applies the merge (list or single id)
        Then the cover is prepended
        """
        self.make_cover()
        for res_ids in ([self.order.id], self.order.id):
            texts = page_texts(self.Report._apply_pdf_merge(res_ids, self.report))
            self.assertEqual(len(texts), 2)
            self.assertIn("cover 1", texts[0])

    def test_apply_merge_without_cover_returns_same_content(self):
        """
        Given no active cover
        When the report layer applies the merge
        Then the very same bytes are returned
        """
        self.assertEqual(
            self.Report._apply_pdf_merge([self.order.id], self.report), self.report
        )

    def test_apply_merge_respects_order_flag(self):
        """
        Given an active cover and an order with Print with Cover unchecked
        When the report layer applies the merge
        Then the report is returned as it came
        """
        self.make_cover()
        self.order.merge_pdf = False
        self.assertEqual(
            self.Report._apply_pdf_merge([self.order.id], self.report), self.report
        )

    def test_apply_merge_skips_missing_orders(self):
        """
        Given an active cover and ids that do not exist
        When the report layer applies the merge
        Then the report is returned as it came
        """
        self.make_cover()
        self.assertEqual(
            self.Report._apply_pdf_merge([999999], self.report), self.report
        )

    def test_apply_merge_survives_invalid_content(self):
        """
        Given an active cover and report content that is not a PDF
        When the report layer applies the merge
        Then the content is returned as it came
        """
        self.make_cover()
        with mute_logger(LOGGER, REPORT_LOGGER, PYPDF):
            result = self.Report._apply_pdf_merge([self.order.id], b"<html/>")
        self.assertEqual(result, b"<html/>")

    def test_apply_merge_survives_unexpected_failure(self):
        """
        Given an active cover and a merge that blows up unexpectedly
        When the report layer applies the merge
        Then the original report is returned instead of an error
        """
        self.make_cover()
        order_model = type(self.order)
        with mute_logger(REPORT_LOGGER), patch.object(
            order_model, "merge_with_cover_pdf", side_effect=RuntimeError("boom")
        ):
            result = self.Report._apply_pdf_merge([self.order.id], self.report)
        self.assertEqual(result, self.report)

    def test_get_report_from_name_returns_the_sale_report(self):
        """
        Given the technical name of the sale order report
        When it is looked up through the overridden method
        Then the standard report record is returned
        """
        report = self.Report._get_report_from_name("sale.report_saleorder")
        self.assertEqual(report, self.env.ref("sale.action_report_saleorder"))

    def test_is_sale_order_report_with_invalid_reference(self):
        """
        Given a malformed report reference
        When checking whether it is a sale order report
        Then the lookup error is swallowed and the answer is False
        """
        with mute_logger(REPORT_LOGGER):
            self.assertFalse(self.Report._is_sale_order_report("malformed", []))

    def test_rendered_sale_report_gets_the_cover(self):
        """
        Given an active cover
        When the standard sale order report goes through the PDF rendering
        Then the cover page comes before the rendered report pages
        """
        Report = self.Report.with_context(force_report_rendering=True)
        ref = "sale.action_report_saleorder"
        company = self.order.company_id
        if "sale_header" in company._fields:
            # keep the auto installed sale_pdf_quote_builder pages out of the count
            company.write({"sale_header": False, "sale_footer": False})
        # mocked as in the core report tests: the binary hangs in CI
        with patch.object(
            type(self.Report), "_run_wkhtmltopdf", return_value=self.report
        ) as wkhtmltopdf:
            self.order.merge_pdf = False
            plain, _fmt = Report._render_qweb_pdf(ref, self.order.ids)
            self.make_cover(pages=1)
            self.order.merge_pdf = True
            merged, report_format = Report._render_qweb_pdf(ref, self.order.ids)
        self.assertEqual(wkhtmltopdf.call_count, 2)
        self.assertIn(self.order.name, wkhtmltopdf.call_args.args[0][0])
        self.assertEqual(plain, self.report)
        self.assertEqual(report_format, "pdf")
        texts = page_texts(merged)
        self.assertEqual(len(texts), 2)
        self.assertIn("cover 1", texts[0])
        self.assertIn("report 1", texts[1])

    def test_is_sale_order_report_detection(self):
        """
        Given a sale report record, its xml id, sale order ids and unrelated input
        When checking whether it is a sale order report
        Then only the sale related inputs are accepted
        """
        sale_report = self.env.ref("sale.action_report_saleorder")
        other_report = self.env.ref("base.ir_module_reference_print")
        Report = self.env["ir.actions.report"]
        self.assertTrue(Report._is_sale_order_report(sale_report, []))
        self.assertTrue(
            Report._is_sale_order_report("sale.action_report_saleorder", None)
        )
        self.assertTrue(Report._is_sale_order_report(other_report, [self.order.id]))
        self.assertTrue(Report._is_sale_order_report(other_report, self.order.id))
        self.assertFalse(Report._is_sale_order_report(other_report, [999999]))
        self.assertFalse(Report._is_sale_order_report(other_report, []))
        self.assertTrue(sale_report._is_sale_order_report(other_report, []))
