import logging
from urllib.parse import urlparse

from lxml import html
from lxml.etree import ParserError

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _svg_sanitize_get_host_port(self, url):
        """Return normalized (host, port) from a URL or None when unavailable."""
        if not url:
            return None

        parsed = urlparse(url)
        if not parsed.scheme and url.startswith("//"):
            parsed = urlparse(f"http:{url}")

        host = parsed.hostname
        if not host:
            return None

        port = parsed.port
        if not port:
            if parsed.scheme == "http":
                port = 80
            elif parsed.scheme == "https":
                port = 443

        return host.lower(), port

    def _svg_sanitize_should_remove(self, src, trusted_host_port):
        """Decide if an <img> src should be removed as an external SVG."""
        if not src:
            return False

        src_lower = src.lower()

        # Keep inline/data and relative/cid sources.
        if src_lower.startswith(("data:", "cid:")):
            return False

        parsed = urlparse(src)
        if not parsed.scheme and src.startswith("//"):
            parsed = urlparse(f"http:{src}")

        # Relative paths (no scheme/netloc) are considered trusted.
        if not parsed.scheme and not parsed.netloc:
            return False

        # Skip non HTTP/HTTPS protocols.
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return False

        candidate = self._svg_sanitize_get_host_port(parsed.geturl())
        if candidate is None or trusted_host_port is None:
            return False

        candidate_host, candidate_port = candidate
        trusted_host, trusted_port = trusted_host_port

        if candidate_host != trusted_host:
            return True

        if trusted_port and candidate_port and candidate_port != trusted_port:
            return True

        return False

    def _sanitize_external_svg_images(self, body):
        """Remove external SVG images from a HTML body."""
        if not body or ".svg" not in body.lower():
            return body, 0

        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        ).rstrip("/")
        trusted_host_port = self._svg_sanitize_get_host_port(base_url)

        try:
            tree = html.fromstring(body)
        except (ValueError, ParserError) as exc:
            _logger.warning("SVG sanitizer could not parse body: %s", exc)
            return body, 0

        removed = 0
        xpath_expr = '//img[contains(translate(@src, "SVG", "svg"), ".svg")]'

        for img in tree.xpath(xpath_expr):
            src = img.get("src") or ""
            if self._svg_sanitize_should_remove(src, trusted_host_port):
                parent = img.getparent()
                if parent is not None:
                    parent.remove(img)
                    removed += 1
                    _logger.debug("Removed external SVG image: %s", src)

        if not removed:
            return body, 0

        cleaned_body = html.tostring(tree, encoding="unicode", method="html")
        return cleaned_body, removed

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        body = message_dict.get("body")
        cleaned_body, removed = self._sanitize_external_svg_images(body)

        if removed:
            message_dict["body"] = cleaned_body

        return super()._message_route_process(message, message_dict, routes)
