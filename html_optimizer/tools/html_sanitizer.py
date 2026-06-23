# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure HTML optimization helpers (no Odoo dependency).

Cleans up heavy email/description HTML and produces a visible-character-bounded
summary, so large bodies render fast while the full content stays available.
"""

import hashlib
import re
from copy import deepcopy

from lxml import etree, html as lxml_html


class HtmlSanitizer:
    MAX_DESCRIPTION_BYTES = 51_200  # 50 KB
    SUMMARY_MAX_CHARS = 1_500
    MAX_CONSECUTIVE_EMPTY_PARAGRAPHS = 2
    MAX_DOM_DEPTH = 15

    def sanitize(self, html: str) -> str:
        """Take raw HTML and return optimized, summarized HTML."""
        if not html:
            return html

        result = self.optimize(html)
        return self.create_summary(result)

    def optimize(self, html: str) -> str:
        """Apply optimizations without summarizing the content."""
        if not html:
            return html

        result = html
        result = self.remove_zero_width_chars(result)
        result = self.normalize_image_styles(result)
        result = self.add_lazy_load_to_images(result)
        result = self.remove_duplicate_blocks(result)
        result = self.collapse_empty_paragraphs(result)
        return result

    def text_content_length(self, html: str) -> int:
        """Return the length of the visible text of the HTML."""
        if not html:
            return 0

        try:
            root = lxml_html.fragment_fromstring(html, create_parent="div")
            return len(root.text_content())
        except (etree.ParserError, ValueError):
            text_content = re.sub(r"<[^>]+>", "", html)
            return len(text_content)

    def has_hidden_content(self, html: str) -> bool:
        return self.text_content_length(html) > self.SUMMARY_MAX_CHARS

    def _truncate_node(self, node, remaining_chars):
        if remaining_chars <= 0:
            return None, 0

        new_node = deepcopy(node)
        new_node.clear()
        new_node.attrib.update(node.attrib)

        if node.text:
            new_node.text = node.text[:remaining_chars]
            remaining_chars -= len(new_node.text)

        for child in node:
            if remaining_chars <= 0:
                break

            new_child, remaining_chars = self._truncate_node(child, remaining_chars)
            if new_child is None:
                break

            new_node.append(new_child)

            if child.tail and remaining_chars > 0:
                new_child.tail = child.tail[:remaining_chars]
                remaining_chars -= len(new_child.tail)

        return new_node, remaining_chars

    def _inner_html(self, parent) -> str:
        parts = []
        if parent.text:
            parts.append(parent.text)
        for child in parent:
            parts.append(etree.tostring(child, encoding="unicode", method="html"))
        return "".join(parts)

    def create_summary(self, html: str, max_chars: int = None) -> str:
        """Create an HTML-safe summary bounded by visible characters."""
        if not html:
            return html

        max_chars = max_chars or self.SUMMARY_MAX_CHARS
        if self.text_content_length(html) <= max_chars:
            return html

        try:
            root = lxml_html.fragment_fromstring(html, create_parent="div")
        except (etree.ParserError, ValueError):
            return html[:max_chars]

        summary_root = etree.Element("div")
        remaining_chars = max_chars

        if root.text and remaining_chars > 0:
            summary_root.text = root.text[:remaining_chars]
            remaining_chars -= len(summary_root.text)

        for child in root:
            if remaining_chars <= 0:
                break
            new_child, remaining_chars = self._truncate_node(child, remaining_chars)
            if new_child is None:
                break
            summary_root.append(new_child)

        return self._inner_html(summary_root)

    def remove_zero_width_chars(self, html: str) -> str:
        """Remove U+FEFF, U+200B and similar zero-width characters."""
        if not html:
            return html
        return re.sub(r"[\uFEFF\u200B\u200C\u200D]", "", html)

    def normalize_image_styles(self, html: str) -> str:
        """Drop inline width/height on <img> and make them responsive.

        Replaces by: style="max-width:100%; height:auto;".
        """
        if not html:
            return html

        def replace_img_style(match):
            style_attr = match.group(1)

            # Remove width/height in inches/cm (with or without decimals).
            new_style = re.sub(
                r"\s*width:\s*[\d.]+\s*(?:in|cm)\s*;?",
                "",
                style_attr,
                flags=re.IGNORECASE,
            )
            new_style = re.sub(
                r"\s*height:\s*[\d.]+\s*(?:in|cm)\s*;?",
                "",
                new_style,
                flags=re.IGNORECASE,
            )

            # Add max-width:100%; height:auto; when missing.
            if "max-width" not in new_style:
                new_style = new_style.strip()
                if new_style and not new_style.endswith(";"):
                    new_style += ";"
                if new_style:
                    new_style += " "
                new_style += "max-width:100%; height:auto;"
                new_style = new_style.strip()

            return f'<img style="{new_style}"'

        result = re.sub(
            r'<img\s+style="([^"]*)"', replace_img_style, html, flags=re.IGNORECASE
        )

        def add_style_to_img(match):
            return '<img style="max-width:100%; height:auto;"' + match.group(0)[5:]

        result = re.sub(
            r"<img(?!\s+style=)", add_style_to_img, result, flags=re.IGNORECASE
        )

        return result

    def add_lazy_load_to_images(self, html: str) -> str:
        """Add loading="lazy" to every image for async loading.

        Keeps loading="eager" when already present (above-the-fold images).
        """
        if not html:
            return html

        def add_lazy_to_img(match):
            full_match = match.group(0)

            if re.search(
                r'\bloading\s*=\s*["\'][^"\']*["\']', full_match, re.IGNORECASE
            ):
                return full_match

            if full_match.rstrip().endswith("/>"):
                return full_match.rstrip()[:-2] + ' loading="lazy"/>'
            return full_match.rstrip()[:-1] + ' loading="lazy">'

        return re.sub(r"<img\s[^>]*>", add_lazy_to_img, html, flags=re.IGNORECASE)

    def remove_duplicate_blocks(self, html: str) -> str:
        """Drop blocks with identical text content, keeping the first.

        Only blocks with at least 100 characters of text are considered.
        """
        if not html:
            return html

        tag_pattern = (
            r"<(div|p|span|section|article|header|footer|aside|main|"
            r"blockquote|pre|table|ul|ol|li|dl|dt|dd)(?:\s[^>]*)?>.*?</\1>"
        )

        seen_hashes = set()
        blocks_to_replace = []

        for match in re.finditer(tag_pattern, html, re.DOTALL | re.IGNORECASE):
            block = match.group(0)
            text_content = re.sub(r"<[^>]+>", "", block)

            if len(text_content) >= 100:
                text_hash = hashlib.sha1(text_content.encode("utf-8")).hexdigest()
                if text_hash in seen_hashes:
                    blocks_to_replace.append(block)
                else:
                    seen_hashes.add(text_hash)

        result = html
        for block in blocks_to_replace:
            result = result.replace(block, "", 1)

        return result

    def collapse_empty_paragraphs(self, html: str) -> str:
        """Reduce runs of empty <p> to MAX_CONSECUTIVE_EMPTY_PARAGRAPHS.

        An empty paragraph holds only whitespace, ``&nbsp;`` and/or ``<br>``
        tags, may carry attributes, and may be separated by whitespace.
        """
        if not html:
            return html

        empty_p = r"<p\b[^>]*>(?:\s|&nbsp;|<br\s*/?>)*</p>"
        keep = self.MAX_CONSECUTIVE_EMPTY_PARAGRAPHS
        run = re.compile(r"(?:%s\s*){%d,}" % (empty_p, keep + 1), re.IGNORECASE)
        replacement = "<p>&nbsp;</p>" * keep

        return run.sub(replacement, html)

        return result

    def truncate(self, html: str) -> tuple:
        """Truncate HTML above MAX_DESCRIPTION_BYTES to a valid closing tag.

        Returns (truncated_html, True) when truncated, else (html, False).
        """
        if not html:
            return (html, False)

        html_bytes = html.encode("utf-8")
        if len(html_bytes) <= self.MAX_DESCRIPTION_BYTES:
            return (html, False)

        truncated = html_bytes[: self.MAX_DESCRIPTION_BYTES].decode(
            "utf-8", errors="ignore"
        )

        last_close_pos = 0
        for match in re.finditer(r"</[a-zA-Z][^>]*>", truncated):
            last_close_pos = match.end()

        if last_close_pos > 0:
            truncated = truncated[:last_close_pos]

        try:
            wrapped = f"<root>{truncated}</root>"
            doc = lxml_html.fromstring(wrapped)
            truncated = "".join(
                etree.tostring(child, encoding="unicode", method="html")
                for child in doc
            )
        except Exception:  # pylint: disable=broad-except
            pass

        return (truncated, True)
