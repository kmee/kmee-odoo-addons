# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import timedelta
from unittest.mock import patch

import requests

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from .test_graph_client import FakeResponse

SLIDE_MODULE = "odoo.addons.website_slides_sharepoint.models.slide_slide"
URL = "https://contoso.sharepoint.com/:b:/s/team/EaBc?e=x"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4"
    "z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def _item(mimetype, name="File", size=1000, **extra):
    item = {
        "id": "ITEM1",
        "name": name,
        "size": size,
        "file": {"mimeType": mimetype},
        "parentReference": {"driveId": "DRIVE1"},
    }
    item.update(extra)
    return item


@tagged("post_install", "-at_install")
class TestSlideSharepointBehavior(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["slide.channel"].create({"name": "Course"})
        cls.graph = cls.env["ms.graph.client"]
        cls.graph_cls = type(cls.graph)

    def _mock(self, item, configured=True):
        self.patch(self.graph_cls, "_is_configured", lambda s: configured)
        self.patch(self.graph_cls, "get_drive_item", lambda s, url: item)

    def _mock_image_content(self):
        self.patch(self.graph_cls, "get_thumbnail_url", lambda s, *a, **k: False)
        self.patch(self.graph_cls, "get_content", lambda s, *a, **k: PNG)

    def _slide(self, category="document", **vals):
        values = {
            "name": "Slide",
            "channel_id": self.channel.id,
            "slide_category": category,
            "url": URL,
        }
        if category in ("document", "infographic"):
            values["source_type"] = "external"
        values.update(vals)
        return self.env["slide.slide"].create(values)

    # ------------------------------------------------------------------
    # Item resolution
    # ------------------------------------------------------------------
    def test_item_is_resolved_into_drive_item_and_mimetype(self):
        """Given a configured Graph, When a SharePoint document is created,
        Then drive id, item id and mime type are stored."""
        self._mock(_item(DOCX))
        slide = self._slide()
        self.assertEqual(
            (
                slide.sharepoint_drive_id,
                slide.sharepoint_item_id,
                slide.sharepoint_mimetype,
            ),
            ("DRIVE1", "ITEM1", DOCX),
        )

    def test_item_is_not_fetched_when_not_configured_or_skipped(self):
        """Given an unconfigured Graph (or the skip context), Then Graph is not
        called and the record is still saved."""
        calls = []
        self.patch(self.graph_cls, "_is_configured", lambda s: False)
        self.patch(self.graph_cls, "get_drive_item", lambda s, url: calls.append(url))
        slide = self._slide()
        self.assertFalse(slide.sharepoint_item_id)
        self.patch(self.graph_cls, "_is_configured", lambda s: True)
        skipped = self.env["slide.slide"].with_context(
            website_slides_skip_fetch_metadata=True
        )
        skipped.create(
            {
                "name": "S",
                "channel_id": self.channel.id,
                "slide_category": "document",
                "source_type": "external",
                "url": URL,
            }
        )
        self.assertEqual(calls, [])

    @mute_logger(SLIDE_MODULE)
    def test_graph_outage_does_not_block_saving(self):
        """Given Graph fails, When creating the slide, Then it is created
        without identifiers (no exception)."""
        self.patch(self.graph_cls, "_is_configured", lambda s: True)

        def fail(s, url):
            raise UserError(_("down"))

        self.patch(self.graph_cls, "get_drive_item", fail)
        slide = self._slide()
        self.assertTrue(slide.exists())
        self.assertFalse(slide.sharepoint_item_id)

    def test_changing_to_a_non_sharepoint_url_clears_identifiers(self):
        """Given a resolved slide, When the URL changes to Google Drive, Then
        the SharePoint identifiers are cleared."""
        self._mock(_item(DOCX))
        slide = self._slide()
        slide.with_context(website_slides_skip_fetch_metadata=True).write(
            {"url": "https://drive.google.com/file/d/ABC/view"}
        )
        self.assertFalse(slide.sharepoint_item_id or slide.sharepoint_mimetype)
        self.assertEqual(slide.source_type, "external")

    # ------------------------------------------------------------------
    # Slide type by mime type
    # ------------------------------------------------------------------
    def test_document_slide_type_follows_the_mime_type(self):
        """Given SharePoint documents of several mime types, Then the native
        slide type is derived from it."""
        cases = (
            (PPTX, "slides"),
            ("application/vnd.ms-powerpoint", "slides"),
            (XLSX, "sheet"),
            ("application/vnd.ms-excel", "sheet"),
            (DOCX, "doc"),
            ("application/vnd.oasis.opendocument.text", "doc"),
            ("image/png", "image"),
            ("application/pdf", "pdf"),
            ("application/zip", "pdf"),
        )
        for mimetype, expected in cases:
            self._mock(_item(mimetype))
            self.assertEqual(self._slide().slide_type, expected, mimetype)

    def test_infographic_is_always_an_image(self):
        """Given a SharePoint infographic, Then its type is image."""
        self._mock(_item("application/pdf"))
        self._mock_image_content()
        slide = self._slide("infographic")
        self.assertEqual(slide.source_type, "sharepoint")
        self.assertEqual(slide.slide_type, "image")

    def test_pdf_conversion_only_for_office_documents(self):
        """Given a PDF and a Word file, Then only the Word one needs the PDF
        conversion; a text file does too."""
        self._mock(_item("application/pdf"))
        self.assertFalse(self._slide()._sharepoint_needs_pdf_conversion())
        self._mock(_item(DOCX))
        self.assertTrue(self._slide()._sharepoint_needs_pdf_conversion())
        self._mock(_item("text/plain"))
        self.assertTrue(self._slide()._sharepoint_needs_pdf_conversion())

    # ------------------------------------------------------------------
    # Embed code and source adaptation
    # ------------------------------------------------------------------
    def test_embed_code_of_a_non_sharepoint_slide_is_untouched(self):
        """Given a Google Drive document, Then no SharePoint embed is built."""
        slide = self._slide(url="https://drive.google.com/file/d/ABC/view")
        self.assertFalse(slide._is_sharepoint_slide())
        self.assertNotIn("/slides/sharepoint/content", slide.embed_code or "")

    def test_infographic_has_no_sharepoint_embed(self):
        """Given a SharePoint infographic, Then it is a SharePoint slide but no
        iframe or video embed is generated."""
        self._mock(_item("image/png"))
        self._mock_image_content()
        slide = self._slide("infographic")
        self.assertTrue(slide._is_sharepoint_slide())
        self.assertNotIn("/slides/sharepoint/content", slide.embed_code or "")

    def test_leaving_sharepoint_falls_back_to_external_source(self):
        """Given a SharePoint document, When its URL becomes a Google link,
        Then the source goes back to external (not left as sharepoint)."""
        self._mock(_item(DOCX))
        slide = self._slide()
        self.assertEqual(slide.source_type, "sharepoint")
        slide.with_context(website_slides_skip_fetch_metadata=True).write(
            {"url": "https://drive.google.com/file/d/ABC/view"}
        )
        self.assertEqual(slide.source_type, "external")

    def test_write_url_with_mixed_categories_keeps_source_types(self):
        """Given a document and a video written together with a SharePoint URL,
        Then the ambiguous batch is left untouched by the adaptation."""
        self._mock(_item(DOCX))
        doc = self._slide()
        doc.source_type = "external"
        video = self._slide("video", url="https://www.youtube.com/watch?v=ebBez6bcSEc")
        (doc | video).with_context(website_slides_skip_fetch_metadata=True).write(
            {"url": URL}
        )
        self.assertEqual(doc.source_type, "external")

    def test_write_url_clears_the_cached_content_url(self):
        """Given a cached content URL, When the URL changes, Then the cache is
        emptied."""
        self._mock(_item(DOCX))
        slide = self._slide()
        slide.sudo().write(
            {
                "sharepoint_content_url": "https://old",
                "sharepoint_content_url_expiry": fields.Datetime.now(),
            }
        )
        slide.write({"url": URL + "&v=2"})
        self.assertFalse(slide.sudo().sharepoint_content_url)
        self.assertFalse(slide.sudo().sharepoint_content_url_expiry)

    def test_sharepoint_image_url_field_writes_through_url(self):
        """Given the SharePoint document link field, When creating with it,
        Then the slide uses the SharePoint source."""
        self._mock(_item(DOCX))
        slide = self.env["slide.slide"].create(
            {
                "name": "S",
                "channel_id": self.channel.id,
                "slide_category": "document",
                "document_sharepoint_url": URL,
            }
        )
        self.assertEqual(slide.source_type, "sharepoint")
        self.assertEqual(slide.url, URL)

    # ------------------------------------------------------------------
    # Content URL cache
    # ------------------------------------------------------------------
    def test_content_url_without_identifiers_is_false(self):
        """Given a slide without SharePoint identifiers, Then there is no
        content URL."""
        slide = self._slide(url="https://drive.google.com/file/d/ABC/view")
        self.assertFalse(slide._sharepoint_get_content_url())

    def test_expired_or_forced_content_url_is_refreshed(self):
        """Given a cached URL that expired, When asked, Then a new one is
        requested; force_refresh refreshes a valid cache too."""
        self._mock(_item(DOCX))
        slide = self._slide()
        urls = iter(["https://u/1", "https://u/2", "https://u/3"])
        self.patch(
            self.graph_cls, "get_content_url", lambda s, d, i, as_pdf=False: next(urls)
        )
        self.assertEqual(slide._sharepoint_get_content_url(), "https://u/1")
        self.assertEqual(slide._sharepoint_get_content_url(), "https://u/1")
        slide.sudo().sharepoint_content_url_expiry = fields.Datetime.now() - timedelta(
            seconds=5
        )
        self.assertEqual(slide._sharepoint_get_content_url(), "https://u/2")
        self.assertEqual(
            slide._sharepoint_get_content_url(force_refresh=True), "https://u/3"
        )
        self.assertGreater(
            slide.sudo().sharepoint_content_url_expiry, fields.Datetime.now()
        )

    def test_content_url_unavailable_is_not_cached(self):
        """Given Graph without a Location, Then the result is False and nothing
        is cached."""
        self._mock(_item(DOCX))
        slide = self._slide()
        self.patch(
            self.graph_cls, "get_content_url", lambda s, d, i, as_pdf=False: False
        )
        self.assertFalse(slide._sharepoint_get_content_url())
        self.assertFalse(slide.sudo().sharepoint_content_url)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def test_native_metadata_is_used_for_other_sources(self):
        """Given a non-SharePoint slide, Then the SharePoint metadata fetch is
        not used."""
        slide = self._slide(url="https://drive.google.com/file/d/ABC/view")
        with patch.object(
            type(slide), "_fetch_sharepoint_metadata"
        ) as sharepoint, patch(
            "odoo.addons.website_slides.models.slide_slide.Slide._fetch_external_metadata",
            return_value=({"name": "native"}, False),
        ):
            values, error = slide._fetch_external_metadata()
        sharepoint.assert_not_called()
        self.assertEqual(values["name"], "native")

    def test_metadata_without_configuration_returns_an_error(self):
        """Given an unconfigured Graph, Then the metadata fetch returns a
        message instead of values."""
        self._mock(_item(DOCX))
        slide = self._slide()
        self.patch(self.graph_cls, "_is_configured", lambda s: False)
        values, error = slide._fetch_external_metadata()
        self.assertFalse(values)
        self.assertIn("not configured", error)

    def test_metadata_graph_error_is_returned_as_message(self):
        """Given Graph failing with a message, Then it comes back as the error."""
        self._mock(_item(DOCX))
        slide = self._slide()

        def fail(s, url):
            raise UserError(_("boom from graph"))

        self.patch(self.graph_cls, "get_drive_item", fail)
        values, error = slide._fetch_external_metadata()
        self.assertEqual((values, error), ({}, "boom from graph"))

    def test_metadata_preview_returns_only_the_thumbnail_url(self):
        """Given image_url_only, Then name and thumbnail URL are returned and
        nothing is downloaded."""
        self._mock(_item(DOCX, name="Handbook.docx"))
        slide = self._slide()
        self.patch(
            self.graph_cls,
            "get_thumbnail_url",
            lambda s, d, i, size="large": "https://t",
        )
        with patch(SLIDE_MODULE + ".requests.get") as get:
            values, error = slide._fetch_external_metadata(image_url_only=True)
        self.assertFalse(error)
        self.assertEqual(values, {"name": "Handbook.docx", "image_url": "https://t"})
        get.assert_not_called()

    def test_metadata_downloads_the_thumbnail_as_image(self):
        """Given a thumbnail, When fetching full metadata, Then the downloaded
        bytes become image_1920; a download failure is tolerated."""
        self._mock(_item("application/zip"))
        slide = self._slide()
        self.patch(
            self.graph_cls,
            "get_thumbnail_url",
            lambda s, d, i, size="large": "https://t",
        )
        with patch(
            SLIDE_MODULE + ".requests.get",
            return_value=FakeResponse(content=b"PNGDATA"),
        ):
            values, error = slide._fetch_external_metadata()
        self.assertEqual(values["image_1920"], base64.b64encode(b"PNGDATA"))
        with mute_logger(SLIDE_MODULE), patch(
            SLIDE_MODULE + ".requests.get", side_effect=requests.ConnectionError("x")
        ):
            values, error = slide._fetch_external_metadata()
        self.assertNotIn("image_1920", values)
        self.assertFalse(error)

    def test_metadata_infographic_downloads_the_content(self):
        """Given a small SharePoint infographic, Then its content becomes the
        image; above the size limit nothing is downloaded."""
        self._mock(_item("image/png", size=100))
        self._mock_image_content()
        slide = self._slide("infographic")
        values, error = slide._fetch_external_metadata()
        self.assertEqual(values["image_1920"], base64.b64encode(PNG))
        self._mock(_item("image/png", size=31 * 1024 * 1024))
        values, error = slide._fetch_external_metadata()
        self.assertNotIn("image_1920", values)

    def test_metadata_document_completion_time_from_pdf(self):
        """Given an Office document, When fetching metadata, Then it is read as
        PDF to estimate the completion time; a read failure is tolerated."""
        self._mock(_item(DOCX))
        slide = self._slide()
        self.patch(
            self.graph_cls, "get_thumbnail_url", lambda s, d, i, size="large": False
        )
        calls = []

        def content(s, drive, item, as_pdf=False):
            calls.append(as_pdf)
            return b"%PDF"

        self.patch(self.graph_cls, "get_content", content)
        with patch.object(type(slide), "_get_completion_time_pdf", return_value=0.5):
            values, error = slide._fetch_external_metadata()
        self.assertEqual(values["completion_time"], 0.5)
        self.assertEqual(calls, [True])

        def fail(s, drive, item, as_pdf=False):
            raise UserError(_("no content"))

        self.patch(self.graph_cls, "get_content", fail)
        values, error = slide._fetch_external_metadata()
        self.assertNotIn("completion_time", values)
        self.assertFalse(error)

    def test_metadata_plain_pdf_is_not_converted(self):
        """Given a PDF document, Then it is downloaded as is (no conversion)."""
        self._mock(_item("application/pdf"))
        slide = self._slide()
        self.patch(
            self.graph_cls, "get_thumbnail_url", lambda s, d, i, size="large": False
        )
        calls = []

        def content(s, drive, item, as_pdf=False):
            calls.append(as_pdf)
            return b"%PDF"

        self.patch(self.graph_cls, "get_content", content)
        with patch.object(type(slide), "_get_completion_time_pdf", return_value=0.0):
            slide._fetch_external_metadata()
        self.assertEqual(calls, [False])

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def test_settings_are_stored_as_config_parameters(self):
        """Given the settings form, When saving credentials and delivery mode,
        Then they land in the config parameters read by the Graph client."""
        settings = self.env["res.config.settings"].create(
            {
                "sharepoint_tenant_id": "T",
                "sharepoint_client_id": "C",
                "sharepoint_client_secret": "S",
                "sharepoint_delivery_mode": "proxy",
            }
        )
        settings.execute()
        get = self.env["ir.config_parameter"].sudo().get_param
        self.assertEqual(get("website_slides_sharepoint.tenant_id"), "T")
        self.assertEqual(get("website_slides_sharepoint.delivery_mode"), "proxy")
        self.assertTrue(self.graph._is_configured())
