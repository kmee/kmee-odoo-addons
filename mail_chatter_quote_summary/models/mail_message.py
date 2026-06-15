# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree, html as lxml_html

from odoo import _, models

from odoo.addons.html_optimizer.tools.html_sanitizer import HtmlSanitizer
from odoo.addons.html_optimizer.tools.quote_boundary import split_history

ENABLED_PARAM = "mail_chatter_quote_summary.enabled"
MODELS_PARAM = "mail_chatter_quote_summary.models"
TARGET_MESSAGE_TYPES = ("email", "comment")


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _quote_summary_enabled(self):
        param = self.env["ir.config_parameter"].sudo().get_param(ENABLED_PARAM, "True")
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

    def _message_format(self, fnames, format_reply=True):
        formatted = super()._message_format(fnames, format_reply=format_reply)
        if not self._quote_summary_enabled():
            return formatted
        allowed_models = self._quote_summary_models()
        by_id = {message.id: message for message in self}
        for vals in formatted:
            message = by_id.get(vals.get("id"))
            if message is None or not message._quote_summary_applies(allowed_models):
                continue
            summary = message._quote_summary_body(vals.get("body") or "")
            if summary is not None:
                vals["body"] = summary
        return formatted

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
        self.check_access_rule("read")
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
