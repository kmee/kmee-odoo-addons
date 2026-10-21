import base64
import logging
import re
from datetime import timedelta

import requests
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Pre-authenticated Microsoft URLs live for about one hour: keep a safety margin.
CONTENT_URL_TTL = 2700  # seconds

# Documents we can hand over to Graph for an on-the-fly PDF conversion.
OFFICE_MIMETYPES = (
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "text/plain",
    "text/rtf",
)

# Only download the file to compute a completion time below this size.
MAX_INTROSPECTION_SIZE = 30 * 1024 * 1024


class SlideSlide(models.Model):
    _inherit = "slide.slide"

    # Matches SharePoint Online / OneDrive for Business on every Microsoft cloud,
    # plus the OneDrive short links. We deliberately do not try to parse the URL
    # any further: Microsoft Graph resolves sharing links, stream.aspx links and
    # direct file URLs for us.
    SHAREPOINT_URL_REGEX = (
        r"^https?://(?:[\w-]+\.sharepoint(?:\.com|\.us|\.de|\.cn)" r"|1drv\.ms)(?:/|$)"
    )

    source_type = fields.Selection(
        selection_add=[("sharepoint", "Retrieve from SharePoint")],
        ondelete={"sharepoint": "set default"},
    )
    slide_type = fields.Selection(
        selection_add=[("sharepoint_video", "SharePoint Video")],
        ondelete={"sharepoint_video": "set null"},
    )
    video_source_type = fields.Selection(selection_add=[("sharepoint", "SharePoint")])
    document_sharepoint_url = fields.Char(
        "SharePoint Document Link",
        related="url",
        readonly=False,
        help="Link of the SharePoint / OneDrive document, obtained with the "
        "'Copy link' or 'Share' button of the Microsoft interface.",
    )
    image_sharepoint_url = fields.Char(
        "SharePoint Image Link", related="url", readonly=False
    )
    sharepoint_drive_id = fields.Char(
        "SharePoint Drive ID", compute="_compute_sharepoint_item", store=True
    )
    sharepoint_item_id = fields.Char(
        "SharePoint Item ID", compute="_compute_sharepoint_item", store=True
    )
    sharepoint_mimetype = fields.Char(
        "SharePoint Mime Type", compute="_compute_sharepoint_item", store=True
    )
    # Cache of the short lived pre-authenticated Microsoft URL. Restricted,
    # because anyone holding that URL can download the file without going
    # through the eLearning access rules — and the native record rules let a
    # non-member read the metadata of the slides of a public course.
    sharepoint_content_url = fields.Char(
        "SharePoint Content URL",
        copy=False,
        groups="website_slides.group_website_slides_officer",
    )
    sharepoint_content_url_expiry = fields.Datetime(
        "SharePoint Content URL Expiry",
        copy=False,
        groups="website_slides.group_website_slides_officer",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_sharepoint_url(self, url):
        return bool(url) and bool(re.match(self.SHAREPOINT_URL_REGEX, url.strip()))

    def _is_sharepoint_slide(self):
        """True when the slide content has to be served from SharePoint."""
        self.ensure_one()
        if self.slide_category == "video":
            return self.video_source_type == "sharepoint"
        if self.slide_category in ("document", "infographic"):
            return self.source_type == "sharepoint"
        return False

    def _sharepoint_needs_pdf_conversion(self):
        """Office documents are converted to PDF by Graph so browsers can render them."""
        self.ensure_one()
        return (
            self.slide_category == "document"
            and self.sharepoint_mimetype in OFFICE_MIMETYPES
        )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("url", "slide_category", "source_type")
    def _compute_sharepoint_item(self):
        """Resolve the SharePoint URL into a (driveId, itemId) pair through Graph.

        Doing it in a stored compute keeps the identifiers in sync whenever the
        URL changes, which a one-shot fetch on create/write would not.
        """
        graph = self.env["ms.graph.client"]
        skip_fetch = self.env.context.get("install_mode") or self.env.context.get(
            "website_slides_skip_fetch_metadata"
        )
        for slide in self:
            if not slide._is_sharepoint_url(slide.url):
                slide.sharepoint_drive_id = False
                slide.sharepoint_item_id = False
                slide.sharepoint_mimetype = False
                continue
            if skip_fetch or not graph._is_configured():
                # Keep whatever we already know instead of wiping the record.
                slide.sharepoint_drive_id = slide.sharepoint_drive_id or False
                slide.sharepoint_item_id = slide.sharepoint_item_id or False
                slide.sharepoint_mimetype = slide.sharepoint_mimetype or False
                continue
            try:
                item = graph.get_drive_item(slide.url.strip())
            except UserError as error:
                # A Graph outage must not prevent the record from being saved.
                _logger.warning(
                    "Could not resolve SharePoint URL %s: %s", slide.url, error
                )
                slide.sharepoint_drive_id = False
                slide.sharepoint_item_id = False
                slide.sharepoint_mimetype = False
                continue
            slide.sharepoint_drive_id = item["parentReference"]["driveId"]
            slide.sharepoint_item_id = item["id"]
            slide.sharepoint_mimetype = (item.get("file") or {}).get(
                "mimeType"
            ) or False

    @api.depends("video_url")
    def _compute_video_source_type(self):
        res = super()._compute_video_source_type()
        for slide in self:
            if not slide.video_source_type and slide._is_sharepoint_url(
                slide.video_url
            ):
                slide.video_source_type = "sharepoint"
        return res

    @api.depends("sharepoint_mimetype")
    def _compute_slide_type(self):
        res = super()._compute_slide_type()
        for slide in self:
            if slide.slide_category == "video" and slide.video_source_type == (
                "sharepoint"
            ):
                slide.slide_type = "sharepoint_video"
            elif (
                slide.slide_category in ("document", "infographic")
                and slide.source_type == "sharepoint"
            ):
                slide.slide_type = slide._sharepoint_document_slide_type()
        return res

    def _sharepoint_document_slide_type(self):
        """Map the SharePoint mime type on the native slide_type values."""
        self.ensure_one()
        mimetype = self.sharepoint_mimetype or ""
        if self.slide_category == "infographic" or mimetype.startswith("image/"):
            return "image"
        if "presentation" in mimetype or "powerpoint" in mimetype:
            return "slides"
        if "spreadsheet" in mimetype or "excel" in mimetype:
            return "sheet"
        if "word" in mimetype or "opendocument.text" in mimetype:
            return "doc"
        return "pdf"

    @api.depends("sharepoint_item_id")
    def _compute_embed_code(self):
        res = super()._compute_embed_code()
        for slide in self:
            if not slide._is_sharepoint_slide():
                continue
            if not slide.id:
                # Memory record used by the upload dialog: nothing to embed yet.
                continue
            content_url = "/slides/sharepoint/content/%s" % slide.id
            if slide.slide_category == "video":
                embed_code = Markup(
                    '<video src="%s" controls="controls" controlsList="nodownload" '
                    'class="o_wslides_sharepoint_video" preload="metadata" '
                    'playsinline="playsinline"></video>'
                ) % (content_url,)
            elif slide.slide_category == "document":
                embed_code = Markup(
                    '<iframe src="%s#toolbar=0" allowFullScreen="true" '
                    'frameborder="0"></iframe>'
                ) % (content_url,)
            else:
                continue
            slide.embed_code = embed_code
            slide.embed_code_external = embed_code
        return res

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sharepoint_adapt_source_type(
                vals,
                vals.get("slide_category") or "document",
                {vals.get("source_type") or "local_file"},
            )
        return super().create(vals_list)

    def write(self, values):
        if "url" in values:
            # The cached pre-authenticated URL points at the previous file.
            values = dict(
                values,
                sharepoint_content_url=False,
                sharepoint_content_url_expiry=False,
            )
            categories = (
                {values["slide_category"]}
                if "slide_category" in values
                else set(self.mapped("slide_category"))
            )
            if len(categories) == 1:
                self._sharepoint_adapt_source_type(
                    values,
                    categories.pop(),
                    {values["source_type"]}
                    if "source_type" in values
                    else set(self.mapped("source_type")),
                )
        return super().write(values)

    def _sharepoint_adapt_source_type(self, vals, slide_category, source_types):
        """Switch documents and images to the SharePoint source when relevant.

        The upload dialog only offers a generic 'external' source, so we derive
        the actual source from the URL itself rather than asking the user twice.

        :param set source_types: the source types the written records have (or
            will have); ambiguous sets are left untouched.
        """
        if slide_category not in ("document", "infographic"):
            return
        url = next(
            (
                vals[field]
                for field in (
                    "url",
                    "document_sharepoint_url",
                    "document_google_url",
                    "image_sharepoint_url",
                    "image_google_url",
                )
                if vals.get(field)
            ),
            False,
        )
        if not url:
            return
        if self._is_sharepoint_url(url):
            vals["source_type"] = "sharepoint"
        elif source_types == {"sharepoint"}:
            # Moving away from SharePoint: fall back on the native external source.
            vals["source_type"] = "external"

    # ------------------------------------------------------------------
    # Content delivery
    # ------------------------------------------------------------------

    def _sharepoint_get_content_url(self, force_refresh=False):
        """Return a pre-authenticated Microsoft URL for this slide content.

        The URL is cached on the record because Graph rate-limits the ``/content``
        endpoint and a video player asks for it on every playback.
        """
        self.ensure_one()
        if not self.sharepoint_drive_id or not self.sharepoint_item_id:
            return False

        now = fields.Datetime.now()
        if (
            not force_refresh
            and self.sharepoint_content_url
            and self.sharepoint_content_url_expiry
            and self.sharepoint_content_url_expiry > now
        ):
            return self.sharepoint_content_url

        content_url = self.env["ms.graph.client"].get_content_url(
            self.sharepoint_drive_id,
            self.sharepoint_item_id,
            as_pdf=self._sharepoint_needs_pdf_conversion(),
        )
        if not content_url:
            return False
        self.sudo().write(
            {
                "sharepoint_content_url": content_url,
                "sharepoint_content_url_expiry": now
                + timedelta(seconds=CONTENT_URL_TTL),
            }
        )
        return content_url

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _fetch_external_metadata(self, image_url_only=False):
        self.ensure_one()
        if self._is_sharepoint_slide():
            return self._fetch_sharepoint_metadata(image_url_only)
        return super()._fetch_external_metadata(image_url_only=image_url_only)

    def _fetch_sharepoint_metadata(self, image_url_only=False):
        """Fetch name, thumbnail and duration of a SharePoint file through Graph.

        :return: a tuple (values, error) mirroring the native fetch methods.
        """
        self.ensure_one()
        graph = self.env["ms.graph.client"]
        if not graph._is_configured():
            return {}, _(
                "The Microsoft 365 integration is not configured. Please contact "
                "your administrator."
            )
        try:
            item = graph.get_drive_item(self.url.strip())
        except UserError as error:
            return {}, error.args and error.args[0] or _("Unknown SharePoint error.")

        drive_id = item["parentReference"]["driveId"]
        item_id = item["id"]
        mimetype = (item.get("file") or {}).get("mimeType") or ""
        values = {"name": item.get("name") or ""}

        duration_ms = (item.get("video") or {}).get("duration")
        if duration_ms:
            values["completion_time"] = duration_ms / 1000.0 / 3600.0

        image_url = graph.get_thumbnail_url(drive_id, item_id)
        if image_url:
            if image_url_only:
                values["image_url"] = image_url
            else:
                image_content = self._sharepoint_download(image_url)
                if image_content:
                    values["image_1920"] = base64.b64encode(image_content)

        if not image_url_only:
            values.update(
                self._fetch_sharepoint_binary_metadata(
                    graph, item, drive_id, item_id, mimetype
                )
            )
        return values, False

    def _fetch_sharepoint_binary_metadata(
        self, graph, item, drive_id, item_id, mimetype
    ):
        """Download the file when it is cheap enough to extract extra metadata."""
        self.ensure_one()
        values = {}
        size = item.get("size") or 0
        if size > MAX_INTROSPECTION_SIZE:
            return values

        if self.slide_category == "infographic":
            content = graph.get_content(drive_id, item_id)
            if content:
                values["image_1920"] = base64.b64encode(content)
        elif self.slide_category == "document" and not self.completion_time:
            as_pdf = mimetype in OFFICE_MIMETYPES
            if as_pdf or mimetype == "application/pdf":
                try:
                    content = graph.get_content(drive_id, item_id, as_pdf=as_pdf)
                except UserError:
                    return values
                completion_time = self._get_completion_time_pdf(content)
                if completion_time:
                    values["completion_time"] = completion_time
        return values

    def _sharepoint_download(self, url):
        """Download a pre-authenticated Microsoft URL, returning bytes or False."""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.warning("Could not download SharePoint content: %s", error)
            return False
        return response.content
