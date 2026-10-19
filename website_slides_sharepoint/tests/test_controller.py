# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import requests

from odoo import _
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

CONTROLLER = "odoo.addons.website_slides_sharepoint.controllers.main"
SLIDE = "odoo.addons.website_slides_sharepoint.models.slide_slide"
URL = "https://contoso.sharepoint.com/:v:/s/team/EaBc?e=x"
CONTENT = "https://pre.auth.example/content/1"


class FakeUpstream:
    def __init__(self, body=b"VIDEO", status_code=200, headers=None, fail=False):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {
            "Content-Type": "video/mp4",
            "Content-Length": str(len(body)),
            "X-Secret": "must-not-leak",
        }
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise requests.HTTPError("expired")

    def iter_content(self, chunk_size=None):
        yield self.body


@tagged("post_install", "-at_install")
class TestSharepointController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["slide.channel"].create(
            {"name": "Public Course", "is_published": True, "visibility": "public"}
        )
        cls.graph_cls = type(cls.env["ms.graph.client"])
        cls.item = {
            "id": "ITEM1",
            "name": "Video.mp4",
            "size": 10,
            "file": {"mimeType": "video/mp4"},
            "video": {"duration": 7200000},
            "parentReference": {"driveId": "DRIVE1"},
        }

    def setUp(self):
        super().setUp()
        self.patch(self.graph_cls, "_is_configured", lambda s: True)
        self.patch(self.graph_cls, "get_drive_item", lambda s, url: self.item)
        self.content_calls = []

        def content_url(s, drive, item, as_pdf=False):
            self.content_calls.append((drive, item, as_pdf))
            return CONTENT

        self.patch(self.graph_cls, "get_content_url", content_url)
        self.patch(self.graph_cls, "get_thumbnail_url", lambda s, *a, **k: False)

    def _slide(self, **vals):
        values = {
            "name": "Onboarding",
            "channel_id": self.channel.id,
            "slide_category": "video",
            "url": URL,
            "is_published": True,
            "is_preview": True,
        }
        values.update(vals)
        return self.env["slide.slide"].create(values)

    def _get(self, slide, **kwargs):
        return self.url_open(
            "/slides/sharepoint/content/%s" % slide.id, allow_redirects=False, **kwargs
        )

    def _user(self, login, group_xmlid):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
                "groups_id": [(6, 0, [self.env.ref(group_xmlid).id])],
            }
        )

    # ------------------------------------------------------------------
    # Content delivery: access
    # ------------------------------------------------------------------
    def test_preview_slide_redirects_anonymous_visitor(self):
        """Given a published preview slide, When an anonymous visitor asks for
        its content, Then he is redirected to the pre-authenticated URL."""
        response = self._get(self._slide())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], CONTENT)
        self.assertEqual(self.content_calls, [("DRIVE1", "ITEM1", False)])

    def test_non_preview_slide_is_forbidden_to_non_members(self):
        """Given a slide that is not a preview, When an anonymous visitor asks,
        Then 403 and no Microsoft URL is requested."""
        response = self._get(self._slide(is_preview=False))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.content_calls)

    def test_members_and_officers_can_get_non_preview_content(self):
        """Given a non-preview slide, Then a channel member and an eLearning
        officer are redirected, a portal user outside the course is not."""
        slide = self._slide(is_preview=False)
        member = self._user("sp_member", "base.group_portal")
        self.channel._action_add_members(member.partner_id)
        officer = self._user(
            "sp_officer", "website_slides.group_website_slides_officer"
        )
        outsider = self._user("sp_outsider", "base.group_portal")
        for user, expected in ((member, 302), (officer, 302), (outsider, 403)):
            self.authenticate(user.login, user.login)
            self.assertEqual(self._get(slide).status_code, expected, user.login)
            self.logout()

    def test_unknown_inactive_or_non_sharepoint_slide_is_404(self):
        """Given an unknown id, an archived slide or a slide not stored in
        SharePoint, Then 404."""
        missing = self.url_open(
            "/slides/sharepoint/content/99999999", allow_redirects=False
        )
        self.assertEqual(missing.status_code, 404)
        archived = self._slide()
        archived.active = False
        self.assertEqual(self._get(archived).status_code, 404)
        native = self._slide(
            url="https://www.youtube.com/watch?v=ebBez6bcSEc",
        )
        self.assertEqual(self._get(native).status_code, 404)

    @mute_logger(CONTROLLER)
    def test_graph_failures_become_404(self):
        """Given Graph raising or returning no URL, Then the visitor sees 404
        (not a server error)."""
        slide = self._slide()

        def fail(s, drive, item, as_pdf=False):
            raise UserError(_("graph down"))

        self.patch(self.graph_cls, "get_content_url", fail)
        self.assertEqual(self._get(slide).status_code, 404)
        self.patch(
            self.graph_cls, "get_content_url", lambda s, d, i, as_pdf=False: False
        )
        self.assertEqual(self._get(slide).status_code, 404)

    # ------------------------------------------------------------------
    # Content delivery: proxy mode
    # ------------------------------------------------------------------
    def _proxy_mode(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "website_slides_sharepoint.delivery_mode", "proxy"
        )

    def test_proxy_mode_streams_content_and_filters_headers(self):
        """Given proxy delivery, When the visitor asks for the video with a
        Range header, Then the bytes are streamed, the Range is forwarded and
        only safe headers are returned."""
        self._proxy_mode()
        slide = self._slide()
        upstream = FakeUpstream(b"VIDEO", status_code=206)
        with patch(CONTROLLER + ".requests.get", return_value=upstream) as get:
            response = self._get(slide, headers={"Range": "bytes=0-4"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"VIDEO")
        self.assertEqual(get.call_args.args[0], CONTENT)
        self.assertEqual(get.call_args.kwargs["headers"], {"Range": "bytes=0-4"})
        self.assertEqual(response.headers["Content-Type"], "video/mp4")
        self.assertNotIn("X-Secret", response.headers)
        self.assertIn("Onboarding", response.headers["Content-Disposition"])

    @mute_logger(CONTROLLER)
    def test_proxy_mode_refreshes_an_expired_url_once(self):
        """Given an expired cached URL, When the stream fails, Then a fresh URL
        is requested and the content is served."""
        self._proxy_mode()
        slide = self._slide()
        answers = [FakeUpstream(fail=True), FakeUpstream(b"OK")]
        with patch(CONTROLLER + ".requests.get", side_effect=answers) as get:
            response = self._get(slide)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(len(self.content_calls), 2)

    @mute_logger(CONTROLLER)
    def test_proxy_mode_gives_up_when_the_refresh_also_fails(self):
        """Given the stream failing twice, Then 404."""
        self._proxy_mode()
        slide = self._slide()
        with patch(
            CONTROLLER + ".requests.get", side_effect=requests.ConnectionError("x")
        ):
            self.assertEqual(self._get(slide).status_code, 404)

    # ------------------------------------------------------------------
    # Upload dialog
    # ------------------------------------------------------------------
    def _preview(self, url=URL, category="video"):
        self.authenticate("admin", "admin")
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "channel_id": self.channel.id,
                "slide_category": category,
                "url": url,
            },
        }
        response = self.url_open(
            "/slides/prepare_preview",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        return response.json()["result"]

    def test_preview_of_a_sharepoint_video_returns_metadata(self):
        """Given a SharePoint link in the upload dialog, Then the preview has
        the file name and the completion time (2 hours)."""
        result = self._preview()
        self.assertEqual(result["name"], "Video.mp4")
        self.assertEqual(result["completion_time"], 2.0)
        self.assertNotIn("error", result)
        self.assertNotIn("info", result)

    def test_preview_warns_about_a_video_already_in_the_channel(self):
        """Given the same SharePoint video already in the channel, Then the
        preview carries an info message naming it."""
        self._slide(name="Existing video")
        result = self._preview()
        self.assertIn("Existing video", result["info"])

    def test_preview_of_a_document_has_no_duplicate_warning(self):
        """Given a SharePoint document, Then no duplicate info is computed."""
        self.item = dict(self.item, file={"mimeType": "application/pdf"}, video=None)
        result = self._preview(category="document")
        self.assertEqual(result["name"], "Video.mp4")
        self.assertNotIn("info", result)

    def test_preview_without_configuration_returns_an_error(self):
        """Given an unconfigured integration, Then the dialog gets an error
        message instead of a traceback."""
        self.patch(self.graph_cls, "_is_configured", lambda s: False)
        self.assertIn("not configured", self._preview()["error"])

    @mute_logger(SLIDE)
    def test_preview_graph_error_is_returned_to_the_dialog(self):
        """Given Graph failing to resolve the link, Then the dialog gets the
        error text."""

        def fail(s, url):
            raise UserError(_("cannot resolve"))

        self.patch(self.graph_cls, "get_drive_item", fail)
        self.assertEqual(self._preview()["error"], "cannot resolve")

    def test_sharepoint_fields_are_accepted_by_the_slide_form(self):
        """Given the controller whitelist, Then the SharePoint link fields are
        valid slide post values."""
        from ..controllers.main import WebsiteSlidesSharepoint

        values = WebsiteSlidesSharepoint()._get_valid_slide_post_values()
        self.assertIn("document_sharepoint_url", values)
        self.assertIn("image_sharepoint_url", values)
        self.assertIn("name", values)
