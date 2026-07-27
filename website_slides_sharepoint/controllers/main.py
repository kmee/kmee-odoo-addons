import logging

import requests
import werkzeug.utils
from werkzeug.exceptions import Forbidden, NotFound

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.website_slides.controllers.main import WebsiteSlides

_logger = logging.getLogger(__name__)

# Headers forwarded to the visitor when streaming through Odoo.
PROXIED_RESPONSE_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
)
STREAM_CHUNK_SIZE = 256 * 1024


class WebsiteSlidesSharepoint(WebsiteSlides):
    # ------------------------------------------------------------------
    # Content delivery
    # ------------------------------------------------------------------

    @http.route(
        "/slides/sharepoint/content/<int:slide_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def slide_sharepoint_content(self, slide_id, **kwargs):
        """Serve the SharePoint content of a slide to the attendee.

        The Odoo server is the only one holding Microsoft credentials, so an
        anonymous attendee can watch a video that is not shared publicly on
        SharePoint. Access is granted by the eLearning rules only.
        """
        slide = self._sharepoint_get_authorized_slide(slide_id)

        try:
            content_url = slide._sharepoint_get_content_url()
        except UserError as error:
            _logger.warning(
                "Could not get the SharePoint content of slide %s: %s", slide.id, error
            )
            raise NotFound() from error
        if not content_url:
            raise NotFound()

        delivery_mode = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("website_slides_sharepoint.delivery_mode", "redirect")
        )
        if delivery_mode == "proxy":
            return self._sharepoint_stream(slide, content_url)
        return werkzeug.utils.redirect(content_url, code=302)

    def _sharepoint_get_authorized_slide(self, slide_id):
        """Return the slide in sudo, once the visitor is allowed to see its content."""
        slide = request.env["slide.slide"].browse(int(slide_id)).exists()
        if not slide:
            raise NotFound()
        try:
            slide.check_access_rights("read")
            slide.check_access_rule("read")
        except AccessError as error:
            raise Forbidden() from error
        if not slide.channel_id.can_access_from_current_website() or not slide.active:
            raise NotFound()

        # Evaluated before sudo(): membership depends on the current user.
        can_see_content = (
            slide.is_preview
            or slide.channel_id.is_member
            or request.env.user.has_group("website_slides.group_website_slides_officer")
        )
        if not can_see_content:
            raise Forbidden()

        slide = slide.sudo()
        if not slide._is_sharepoint_slide():
            raise NotFound()
        return slide

    def _sharepoint_stream(self, slide, content_url):
        """Stream the Microsoft content through Odoo, honouring Range requests.

        Range support is what makes seeking inside a video work; without it the
        browser has to download the whole file before the attendee can skip.
        """
        headers = {}
        if request.httprequest.headers.get("Range"):
            headers["Range"] = request.httprequest.headers["Range"]

        try:
            upstream = requests.get(
                content_url, headers=headers, stream=True, timeout=30
            )
            upstream.raise_for_status()
        except requests.exceptions.RequestException as error:
            # The cached URL may have expired: retry once with a fresh one.
            _logger.info(
                "Refreshing the SharePoint URL of slide %s after: %s", slide.id, error
            )
            try:
                content_url = slide._sharepoint_get_content_url(force_refresh=True)
                upstream = requests.get(
                    content_url, headers=headers, stream=True, timeout=30
                )
                upstream.raise_for_status()
            except (requests.exceptions.RequestException, UserError) as retry_error:
                raise NotFound() from retry_error

        response_headers = [
            (header, upstream.headers[header])
            for header in PROXIED_RESPONSE_HEADERS
            if header in upstream.headers
        ]
        response_headers.append(
            ("Content-Disposition", 'inline; filename="%s"' % slide.name)
        )
        return request.make_response(
            upstream.iter_content(chunk_size=STREAM_CHUNK_SIZE),
            headers=response_headers,
            status=upstream.status_code,
        )

    # ------------------------------------------------------------------
    # Upload dialog
    # ------------------------------------------------------------------

    @http.route()
    def prepare_preview(self, channel_id, slide_category, url=None):
        """Handle SharePoint links in the 'new content' dialog.

        The native implementation only knows about YouTube, Vimeo and Google
        Drive, and rejects anything else before we get a chance to look at it.
        """
        Slide = request.env["slide.slide"]
        if not url or not Slide._is_sharepoint_url(url):
            return super().prepare_preview(channel_id, slide_category, url=url)

        if not request.env["ms.graph.client"]._is_configured():
            return {
                "error": _(
                    "The Microsoft 365 integration is not configured. Please contact "
                    "your administrator."
                )
            }

        slide_values = {
            "channel_id": int(channel_id),
            "name": "memory_record_for_computed_fields",
            "slide_category": slide_category,
            "url": url,
        }
        if slide_category in ("document", "infographic"):
            slide_values["source_type"] = "sharepoint"
        slide = Slide.new(slide_values)

        additional_values = {}
        if slide_category == "video":
            identical_video = Slide.search(
                [
                    ("channel_id", "=", int(channel_id)),
                    ("slide_category", "=", "video"),
                    ("sharepoint_item_id", "=", slide.sharepoint_item_id),
                ],
                limit=1,
            )
            if slide.sharepoint_item_id and identical_video:
                additional_values["info"] = _(
                    "This video already exists in this channel on the following "
                    "content: %s",
                    identical_video.name,
                )

        values, error = slide._fetch_external_metadata(image_url_only=True)
        if error:
            return {"error": error}
        values.update(additional_values)
        return values

    def _get_valid_slide_post_values(self):
        return super()._get_valid_slide_post_values() + [
            "document_sharepoint_url",
            "image_sharepoint_url",
        ]
