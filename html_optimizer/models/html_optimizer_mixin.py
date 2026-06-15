# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree, html as lxml_html

from odoo import api, models

from ..tools.html_sanitizer import HtmlSanitizer

SKIP_CONTEXT = "skip_html_optimizer"


class HtmlOptimizerMixin(models.AbstractModel):
    """Generic per-field HTML optimizer.

    A model inherits this mixin and declares which HTML field(s) to optimize via
    ``_optimizer_fields = {source_field: full_field}``. On create/write the
    source field is sanitized and summarized in place, while the full optimized
    content is kept in the companion field. The full content is then served on
    demand through ``load_optimizer_full_chunk``.
    """

    _name = "html.optimizer.mixin"
    _description = "HTML Optimizer Mixin"

    # {source_field: full_field}; set by the inheriting model.
    _optimizer_fields = {}

    def _optimizer_sanitizer(self):
        return HtmlSanitizer()

    def _optimizer_summarize(self, value):
        """Return (summary, optimized_full) for a raw HTML value."""
        sanitizer = self._optimizer_sanitizer()
        optimized = sanitizer.optimize(value)
        return sanitizer.create_summary(optimized), optimized

    def _optimizer_has_full(self, field):
        self.ensure_one()
        return self._optimizer_sanitizer().has_hidden_content(self[field])

    def _optimizer_apply_vals(self, vals):
        if self.env.context.get(SKIP_CONTEXT):
            return
        for source, full in self._optimizer_fields.items():
            if vals.get(source):
                summary, optimized = self._optimizer_summarize(vals[source])
                vals[source] = summary
                vals[full] = optimized

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._optimizer_apply_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._optimizer_apply_vals(vals)
        return super().write(vals)

    def _optimizer_blocks(self, html):
        if not html:
            return []
        try:
            root = lxml_html.fragment_fromstring(html, create_parent="div")
        except (etree.ParserError, etree.LxmlError, ValueError):
            return [html]
        blocks = []
        if root.text and root.text.strip():
            blocks.append(root.text)
        for child in root:
            blocks.append(etree.tostring(child, encoding="unicode", method="html"))
        return blocks or [html]

    def load_optimizer_full_chunk(self, field, offset=0, chunk_size=25):
        """Stream the full content of ``field`` in block chunks (lazy load)."""
        self.ensure_one()
        if field not in self._optimizer_fields.values():
            raise ValueError("Field %r is not an optimizer full field" % field)
        self.check_access_rule("read")
        blocks = self._optimizer_blocks(self[field] or "")
        offset = max(int(offset or 0), 0)
        chunk_size = max(int(chunk_size or 25), 1)
        chunk = blocks[offset : offset + chunk_size]
        next_offset = (
            offset + chunk_size if offset + chunk_size < len(blocks) else False
        )
        return {"html": "".join(chunk), "next_offset": next_offset, "offset": offset}

    def _optimizer_reprocess(self, batch_size=200):
        """Re-apply optimization to existing records of this model.

        Recomputes summary + full from the full field (source of truth),
        skipping the create/write hook. Commits per batch.
        """
        sanitizer = self._optimizer_sanitizer()
        processed = updated = 0
        last_id = 0
        full_fields = list(self._optimizer_fields.values())
        domain_any = ["|"] * (len(self._optimizer_fields) - 1) + [
            (source, "!=", False) for source in self._optimizer_fields
        ]
        while True:
            records = self.search(
                domain_any + [("id", ">", last_id)],
                order="id asc",
                limit=batch_size,
            )
            if not records:
                break
            for record in records:
                processed += 1
                changes = {}
                for source, full in self._optimizer_fields.items():
                    raw = record[full] or record[source]
                    if not raw or not sanitizer.has_hidden_content(raw):
                        continue
                    summary, optimized = self._optimizer_summarize(raw)
                    changes[source] = summary
                    changes[full] = optimized
                if changes:
                    record.with_context(**{SKIP_CONTEXT: True}).write(changes)
                    updated += 1
            last_id = records[-1].id
            self.env.cr.commit()  # pylint: disable=invalid-commit
        return {"processed": processed, "updated": updated, "full_fields": full_fields}
