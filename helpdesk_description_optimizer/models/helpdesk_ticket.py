from lxml import etree, html

from odoo import api, fields, models

from .html_sanitizer import HtmlSanitizer


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    REPROCESS_BATCH_SIZE = 200

    description_full = fields.Html(
        string="Descrição Completa",
        sanitize=False,
    )
    has_description_full = fields.Boolean(
        compute="_compute_has_description_full",
    )

    @api.depends("description_full")
    def _compute_has_description_full(self):
        sanitizer = HtmlSanitizer()
        for ticket in self:
            ticket.has_description_full = sanitizer.has_hidden_content(
                ticket.description_full
            )

    def _sanitize_description(self, description):
        """Aplica sanitização ao HTML da descrição."""
        if not description:
            return description, description

        sanitizer = HtmlSanitizer()
        optimized = sanitizer.optimize(description)
        summary = sanitizer.create_summary(optimized)
        return summary, optimized

    def _get_description_full_blocks(self):
        self.ensure_one()
        description = self.description_full or self.description or ""
        if not description:
            return []

        try:
            root = html.fromstring(f"<div>{description}</div>")
        except (etree.ParserError, ValueError):
            return [description]

        blocks = []
        if root.text and root.text.strip():
            blocks.append(root.text)

        for child in root:
            blocks.append(html.tostring(child, encoding="unicode"))
            if child.tail and child.tail.strip():
                blocks.append(child.tail)

        return blocks or [description]

    def load_description_full_chunk(self, offset=0, chunk_size=25):
        self.ensure_one()
        offset = max(int(offset or 0), 0)
        chunk_size = max(int(chunk_size or 25), 1)

        blocks = self._get_description_full_blocks()
        chunk = blocks[offset : offset + chunk_size]
        next_offset = (
            offset + chunk_size if offset + chunk_size < len(blocks) else False
        )

        return {
            "html": "".join(chunk),
            "next_offset": next_offset,
            "offset": offset,
        }

    def reprocess_description_queue_job(self, wizard_id=None):
        sanitizer = HtmlSanitizer()
        processed = 0
        updated = 0
        log_lines = []
        last_id = 0

        while True:
            tickets = self.search(
                [
                    ("description", "!=", False),
                    ("id", ">", last_id),
                ],
                order="id ASC",
                limit=self.REPROCESS_BATCH_SIZE,
            )
            if not tickets:
                break

            for ticket in tickets:
                processed += 1
                source_html = ticket.description_full or ticket.description
                if not sanitizer.has_hidden_content(source_html):
                    continue

                summary, full = ticket._sanitize_description(source_html)
                ticket.with_context(
                    skip_description_optimization=True,
                    tracking_disable=True,
                    mail_notrack=True,
                    mail_create_nolog=True,
                ).write(
                    {
                        "description": summary,
                        "description_full": full,
                    }
                )
                updated += 1
                log_lines.append(f"Ticket #{ticket.id}: atualizado")

            last_id = tickets[-1].id

        if wizard_id:
            wizard = self.env["helpdesk.ticket.reprocess.wizard"].browse(wizard_id)
            if wizard.exists():
                wizard.write(
                    {
                        "state": "done",
                        "processed_count": processed,
                        "updated_count": updated,
                        "log_text": "\n".join(log_lines) + f"\n\n=== Conclusão ===\n"
                        f"Tickets processados: {processed}\n"
                        f"Tickets atualizados: {updated}\n"
                        "Status: Concluído com sucesso!",
                    }
                )

        return {
            "processed": processed,
            "updated": updated,
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Override de create para salvar description_full e sanitizar description."""
        # Processa todos os valores antes de criar
        if not self.env.context.get("skip_description_optimization"):
            for vals in vals_list:
                if "description" in vals and vals["description"]:
                    sanitized, original = self._sanitize_description(
                        vals["description"]
                    )
                    vals["description"] = sanitized
                    vals["description_full"] = original

        # Chama o super() que pode ser ag_helpdesk ou helpdesk
        return super().create(vals_list)

    def write(self, vals):
        """Override de write para salvar description_full e sanitizar description."""
        if (
            not self.env.context.get("skip_description_optimization")
            and "description" in vals
            and vals["description"]
        ):
            sanitized, original = self._sanitize_description(vals["description"])
            vals["description"] = sanitized
            vals["description_full"] = original

        # Chama o super() que pode ser ag_helpdesk ou helpdesk
        return super().write(vals)
