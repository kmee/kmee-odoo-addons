# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree, html as lxml_html
from markupsafe import Markup

from odoo import _, models

from odoo.addons.html_optimizer.tools.html_sanitizer import HtmlSanitizer
from odoo.addons.html_optimizer.tools.quote_boundary import split_history

ENABLED_PARAM = "mail_chatter_quote_summary.enabled"
MODELS_PARAM = "mail_chatter_quote_summary.models"
TARGET_MESSAGE_TYPES = ("email", "comment")


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _quote_summary_enabled(self):
        param = self.env["ir.config_parameter"].sudo().get_param(ENABLED_PARAM, "False")
        return param not in ("False", "0", "", False)

    def _quote_summary_models(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(MODELS_PARAM, "") or ""
        return {name.strip() for name in raw.split(",") if name.strip()}

    def _quote_summary_applies(self, allowed_models):
        self.ensure_one()
        if self.message_type not in TARGET_MESSAGE_TYPES:
            return False
        if allowed_models and self.model not in allowed_models:
            return False
        return True

    def _quote_summary_body(self, body):
        """Return the summarized body (main reply + a lazy toggle), or None."""
        split = split_history(body)
        if not split:
            return None
        main, _history = split
        main = HtmlSanitizer().optimize(main)
        toggle = (
            '<div class="o_quote_history" data-mail-message-id="%d">'
            '<a href="#" class="o_quote_history_btn">%s</a></div>'
            % (self.id, _("Ler mais"))
        )
        return main + toggle

    def _to_store(self, store, /, *, fields=None, **kwargs):
        res = super()._to_store(store, fields=fields, **kwargs)
        if fields is not None and "body" not in fields:
            return res
        if not self._quote_summary_enabled():
            return res
        allowed_models = self._quote_summary_models()
        sanitizer = HtmlSanitizer()
        for message in self:
            if not message._quote_summary_applies(allowed_models):
                continue
            body = message.body or ""
            summary = message._quote_summary_body(body)
            if summary is not None:
                store.add(message, {"body": Markup(summary)})
                continue
            compact = sanitizer.collapse_empty_paragraphs(
                sanitizer.remove_zero_width_chars(body)
            )
            if compact != body:
                store.add(message, {"body": Markup(compact)})
        return res

    def _quote_history_blocks(self, history_html):
        try:
            root = lxml_html.fragment_fromstring(history_html, create_parent="div")
        except (etree.ParserError, etree.LxmlError, ValueError):
            return [history_html] if history_html else []
        blocks = []
        if root.text and root.text.strip():
            blocks.append(root.text)
        for child in root:
            blocks.append(etree.tostring(child, encoding="unicode", method="html"))
        return blocks

    def load_quote_history_chunk(self, offset=0, chunk_size=25):
        """Lazily stream the quoted history of this message, in block chunks.

        Reads the original (untouched) ``body``; only the rendered payload was
        summarized, so no stored data is lost.
        """
        self.ensure_one()
        self.check_access("read")
        split = split_history(self.body or "")
        if not split:
            return {"html": "", "next_offset": False, "offset": 0}
        _main, history = split
        blocks = self._quote_history_blocks(history)
        offset = max(int(offset or 0), 0)
        chunk_size = max(int(chunk_size or 25), 1)
        chunk = blocks[offset : offset + chunk_size]
        next_offset = (
            offset + chunk_size if offset + chunk_size < len(blocks) else False
        )
        return {"html": "".join(chunk), "next_offset": next_offset, "offset": offset}
