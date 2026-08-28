from lxml import etree

from odoo.tests.common import TransactionCase

from ..models.html_sanitizer import HtmlSanitizer


class TestHelpdeskTicketOptimizer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sanitizer = HtmlSanitizer()
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {
                "name": "Description Optimizer Test Team",
                "alias_name": "description-optimizer-test",
            }
        )

    def _create_ticket(self, description):
        return self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket Teste",
                "description": description,
                "team_id": self.team.id,
            }
        )

    def _big_html(self, kb=100):
        chunks = []
        target_size = kb * 1024
        index = 0
        while len("".join(chunks).encode()) < target_size:
            chunks.append(f"<p>{index}-" + ("x" * 100) + "</p>")
            index += 1
        return "".join(chunks)

    def test_description_full_saved_on_create(self):
        """Criar ticket com HTML grande salva description_full."""
        big = self._big_html(100)
        ticket = self._create_ticket(big)
        self.assertTrue(ticket.description_full)
        self.assertGreater(len(ticket.description_full), len(ticket.description or ""))

    def test_description_truncated_on_create(self):
        """description deve ter no máximo 1500 chars visíveis após create."""
        big = self._big_html(100)
        ticket = self._create_ticket(big)
        self.assertLessEqual(
            self.sanitizer.text_content_length(ticket.description or ""),
            HtmlSanitizer.SUMMARY_MAX_CHARS,
        )
        self.assertTrue(ticket.has_description_full)

    def test_description_full_saved_on_write(self):
        """Ao fazer write com HTML grande, description_full deve ser atualizado."""
        ticket = self._create_ticket("<p>original</p>")
        big = self._big_html(100)
        ticket.write({"description": big})
        self.assertTrue(ticket.description_full)
        self.assertGreater(len(ticket.description_full), len(ticket.description or ""))

    def test_description_truncated_on_write(self):
        ticket = self._create_ticket("<p>original</p>")
        big = self._big_html(100)
        ticket.write({"description": big})
        self.assertLessEqual(
            self.sanitizer.text_content_length(ticket.description or ""),
            HtmlSanitizer.SUMMARY_MAX_CHARS,
        )
        self.assertTrue(ticket.has_description_full)

    def test_small_description_not_split(self):
        """HTML pequeno: description e description_full iguais."""
        small = "<p>Texto curto</p>"
        ticket = self._create_ticket(small)
        self.assertIn("Texto curto", ticket.description or "")
        self.assertIn("Texto curto", ticket.description_full or "")
        self.assertEqual(ticket.description, ticket.description_full)
        self.assertFalse(ticket.has_description_full)

    def test_zero_width_chars_removed_on_save(self):
        ticket = self._create_ticket("<p>\ufeffTexto com BOM</p>")
        self.assertNotIn("\ufeff", ticket.description or "")

    def test_image_styles_normalized_on_save(self):
        html = '<img style="width:15in; height:3in" src="/img">'
        ticket = self._create_ticket(html)
        self.assertNotIn("15in", ticket.description or "")
        self.assertIn("max-width:100%", ticket.description or "")

    def test_duplicate_disclaimers_removed_on_save(self):
        disclaimer = (
            "<div>**** Caso tenha recebido indevidamente delete este e-mail. "
            "In case you received this improperly please delete immediately. ****</div>"
        )
        html = "<p>Conteúdo real</p>" + disclaimer * 5
        ticket = self._create_ticket(html)
        self.assertEqual((ticket.description or "").count("Caso tenha recebido"), 1)

    def test_truncated_description_remains_parseable_with_nested_html(self):
        chunk = "<div><section><p>" + ("x" * 400) + "</p></section></div>"
        html = chunk * 200
        ticket = self._create_ticket(html)
        try:
            etree.fromstring(f"<root>{ticket.description}</root>")
            parseable = True
        except etree.XMLSyntaxError:
            parseable = False
        self.assertTrue(parseable)

    def test_load_description_full_chunk_reconstructs_original_html(self):
        html = "<p>Primeiro</p><p>Segundo</p><p>Terceiro</p>"
        ticket = self._create_ticket(html)

        chunk_1 = ticket.load_description_full_chunk(offset=0, chunk_size=1)
        chunk_2 = ticket.load_description_full_chunk(
            offset=chunk_1["next_offset"], chunk_size=1
        )
        chunk_3 = ticket.load_description_full_chunk(
            offset=chunk_2["next_offset"], chunk_size=1
        )

        rebuilt = chunk_1["html"] + chunk_2["html"] + chunk_3["html"]

        self.assertEqual(rebuilt, ticket.description_full)
        self.assertFalse(chunk_3["next_offset"])

    def test_reprocess_description_queue_job_updates_existing_tickets(self):
        original = "<p>" + ("x" * 2000) + "</p>"
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket legado",
                "description": original,
                "description_full": False,
                "team_id": self.team.id,
            }
        )
        result = self.env["helpdesk.ticket"].reprocess_description_queue_job()
        ticket.invalidate_recordset()

        self.assertGreaterEqual(result["processed"], 1)
        self.assertGreaterEqual(result["updated"], 1)
        self.assertTrue(ticket.description_full)
        self.assertTrue(ticket.has_description_full)

    def test_reprocess_description_queue_job_skips_short_tickets(self):
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket curto",
                "description": "<p>Texto curto</p>",
                "description_full": "<p>Texto curto</p>",
                "team_id": self.team.id,
            }
        )

        result = self.env["helpdesk.ticket"].reprocess_description_queue_job()
        ticket.invalidate_recordset()

        self.assertGreaterEqual(result["processed"], 1)
        self.assertEqual(ticket.description, "<p>Texto curto</p>")
        self.assertEqual(ticket.description_full, "<p>Texto curto</p>")
        self.assertFalse(ticket.has_description_full)
