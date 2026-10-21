import base64

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

VIDEO_SHARE_URL = "https://contoso.sharepoint.com/:v:/s/team/EaBcDeF123?e=xYz789"
DOC_SHARE_URL = "https://contoso.sharepoint.com/:b:/s/team/EaBcDeF456?e=xYz789"

VIDEO_ITEM = {
    "id": "01ABCDEF123456789",
    "name": "Onboarding.mp4",
    "size": 12345678,
    "file": {"mimeType": "video/mp4"},
    "video": {"duration": 3600000},  # 1 hour, in milliseconds
    "parentReference": {"driveId": "b!driveid"},
}
DOCX_ITEM = {
    "id": "01ABCDEF987654321",
    "name": "Handbook.docx",
    "size": 456789,
    "file": {
        "mimeType": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    },
    "parentReference": {"driveId": "b!driveid"},
}


@tagged("post_install", "-at_install")
class TestSlideSharepoint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["slide.channel"].create({"name": "SharePoint Course"})
        cls.graph = cls.env["ms.graph.client"]

    def _mock_graph(self, item):
        """Make the Graph client answer with a static driveItem."""
        graph_cls = type(self.graph)
        self.patch(graph_cls, "_is_configured", lambda self: True)
        self.patch(graph_cls, "get_drive_item", lambda self, url: item)
        self.patch(
            graph_cls,
            "get_content_url",
            lambda self, drive_id, item_id, as_pdf=False: (
                "https://contoso.sharepoint.com/preauth/%s?pdf=%s"
                % (item_id, int(as_pdf))
            ),
        )
        self.patch(graph_cls, "get_thumbnail_url", lambda self, *a, **kw: False)
        self.patch(graph_cls, "get_content", lambda self, *a, **kw: b"")

    # ------------------------------------------------------------------
    # URL detection
    # ------------------------------------------------------------------

    def test_is_sharepoint_url(self):
        Slide = self.env["slide.slide"]
        for url in (
            VIDEO_SHARE_URL,
            "https://contoso-my.sharepoint.com/:v:/g/personal/user_contoso_com/EaBc",
            "https://contoso.sharepoint.com/sites/team/_layouts/15/stream.aspx?id=%2F",
            "https://1drv.ms/v/s!AbCdEf",
        ):
            self.assertTrue(Slide._is_sharepoint_url(url), url)

        for url in (
            "https://www.youtube.com/watch?v=ebBez6bcSEc",
            "https://drive.google.com/file/d/ABC/view",
            "https://vimeo.com/558907333",
            "https://evil.com/?x=contoso.sharepoint.com/",
            False,
        ):
            self.assertFalse(Slide._is_sharepoint_url(url), url)

    def test_encode_share_url(self):
        """The sharing token must be unpadded base64url, prefixed with 'u!'."""
        token = self.graph._encode_share_url(VIDEO_SHARE_URL)
        self.assertTrue(token.startswith("u!"))
        self.assertNotIn("=", token)
        self.assertNotIn("/", token[2:])
        self.assertNotIn("+", token[2:])
        padded = token[2:].replace("_", "/").replace("-", "+")
        padded += "=" * (-len(padded) % 4)
        self.assertEqual(base64.b64decode(padded).decode(), VIDEO_SHARE_URL)

    # ------------------------------------------------------------------
    # Video slides
    # ------------------------------------------------------------------

    def test_video_source_type(self):
        self._mock_graph(VIDEO_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Onboarding",
                "channel_id": self.channel.id,
                "slide_category": "video",
                "url": VIDEO_SHARE_URL,
            }
        )
        self.assertEqual(slide.video_source_type, "sharepoint")
        self.assertEqual(slide.slide_type, "sharepoint_video")
        self.assertEqual(slide.sharepoint_drive_id, "b!driveid")
        self.assertEqual(slide.sharepoint_item_id, VIDEO_ITEM["id"])
        self.assertTrue(slide._is_sharepoint_slide())

    def test_video_embed_code(self):
        self._mock_graph(VIDEO_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Onboarding",
                "channel_id": self.channel.id,
                "slide_category": "video",
                "url": VIDEO_SHARE_URL,
            }
        )
        self.assertIn("<video", slide.embed_code)
        self.assertIn("/slides/sharepoint/content/%s" % slide.id, slide.embed_code)
        self.assertEqual(slide.embed_code_external, slide.embed_code)

    def test_video_metadata(self):
        """Duration comes back from Graph in milliseconds, stored in hours."""
        self._mock_graph(VIDEO_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "channel_id": self.channel.id,
                "slide_category": "video",
                "name": "placeholder",
                "url": VIDEO_SHARE_URL,
            }
        )
        values, error = slide._fetch_external_metadata()
        self.assertFalse(error)
        self.assertEqual(values["name"], "Onboarding.mp4")
        self.assertEqual(values["completion_time"], 1.0)

    def test_native_sources_untouched(self):
        """A YouTube slide must keep going through the native implementation."""
        self._mock_graph(VIDEO_ITEM)
        slide = (
            self.env["slide.slide"]
            .with_context(website_slides_skip_fetch_metadata=True)
            .create(
                {
                    "name": "Youtube",
                    "channel_id": self.channel.id,
                    "slide_category": "video",
                    "url": "https://www.youtube.com/watch?v=ebBez6bcSEc",
                }
            )
        )
        self.assertEqual(slide.video_source_type, "youtube")
        self.assertEqual(slide.slide_type, "youtube_video")
        self.assertFalse(slide.sharepoint_item_id)
        self.assertIn("youtube-nocookie.com", slide.embed_code)

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def test_document_source_type_is_adapted(self):
        """A SharePoint link switches the source type without asking the user."""
        self._mock_graph(DOCX_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Handbook",
                "channel_id": self.channel.id,
                "slide_category": "document",
                "source_type": "external",
                "url": DOC_SHARE_URL,
            }
        )
        self.assertEqual(slide.source_type, "sharepoint")
        self.assertEqual(slide.slide_type, "doc")
        self.assertTrue(slide._sharepoint_needs_pdf_conversion())
        self.assertIn("<iframe", slide.embed_code)
        self.assertIn("/slides/sharepoint/content/%s" % slide.id, slide.embed_code)

    def test_document_back_to_google_drive(self):
        self._mock_graph(DOCX_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Handbook",
                "channel_id": self.channel.id,
                "slide_category": "document",
                "source_type": "external",
                "url": DOC_SHARE_URL,
            }
        )
        slide.with_context(website_slides_skip_fetch_metadata=True).write(
            {"url": "https://drive.google.com/file/d/ABC/view"}
        )
        self.assertEqual(slide.source_type, "external")
        self.assertFalse(slide.sharepoint_item_id)
        self.assertFalse(slide.sharepoint_content_url)

    # ------------------------------------------------------------------
    # Content URL cache
    # ------------------------------------------------------------------

    def test_content_url_is_cached(self):
        self._mock_graph(VIDEO_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Onboarding",
                "channel_id": self.channel.id,
                "slide_category": "video",
                "url": VIDEO_SHARE_URL,
            }
        )
        content_url = slide._sharepoint_get_content_url()
        self.assertIn(VIDEO_ITEM["id"], content_url)
        self.assertEqual(slide.sharepoint_content_url, content_url)
        self.assertTrue(slide.sharepoint_content_url_expiry)

        # A second call must not hit Graph again.
        self.patch(
            type(self.graph),
            "get_content_url",
            lambda *a, **kw: self.fail("Graph was called although the URL is cached"),
        )
        self.assertEqual(slide._sharepoint_get_content_url(), content_url)

    def test_content_url_is_not_readable_by_attendees(self):
        """The pre-authenticated URL bypasses the eLearning rules: keep it hidden.

        A non-member can read the metadata of the slides of a public course, so
        an unrestricted field would hand them a direct download link.
        """
        self._mock_graph(VIDEO_ITEM)
        self.channel.write({"is_published": True, "visibility": "public"})
        slide = self.env["slide.slide"].create(
            {
                "name": "Onboarding",
                "channel_id": self.channel.id,
                "slide_category": "video",
                "url": VIDEO_SHARE_URL,
                "is_published": True,
                "is_preview": True,
            }
        )
        slide._sharepoint_get_content_url()

        attendee = self.env["res.users"].create(
            {
                "name": "Attendee",
                "login": "attendee@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        attendee_slide = slide.with_user(attendee)
        # The lesson itself stays readable...
        self.assertEqual(attendee_slide.read(["name"])[0]["name"], "Onboarding")
        # ... but not the Microsoft URL.
        with self.assertRaises(AccessError):
            attendee_slide.read(["sharepoint_content_url"])

    def test_content_url_pdf_conversion(self):
        """Office documents are requested as PDF so that browsers can render them."""
        self._mock_graph(DOCX_ITEM)
        slide = self.env["slide.slide"].create(
            {
                "name": "Handbook",
                "channel_id": self.channel.id,
                "slide_category": "document",
                "source_type": "external",
                "url": DOC_SHARE_URL,
            }
        )
        self.assertIn("pdf=1", slide._sharepoint_get_content_url())
