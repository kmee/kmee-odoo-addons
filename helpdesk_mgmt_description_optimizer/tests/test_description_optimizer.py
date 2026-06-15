# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase


class TestDescriptionOptimizer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {"name": "Description Optimizer Test Team"}
        )

    def _big_description(self, visible_chars=3000):
        return (
            "<div>"
            + "".join(
                "<p>Linha %d de conteudo sem dados pessoais.</p>" % i
                for i in range(visible_chars // 40 + 1)
            )
            + "</div>"
        )

    def _create_ticket(self, description):
        return self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket Teste",
                "description": description,
                "team_id": self.team.id,
            }
        )

    def test_full_kept_and_summary_shorter(self):
        big = self._big_description()
        ticket = self._create_ticket(big)
        self.assertTrue(ticket.description_full)
        self.assertTrue(ticket.has_description_full)
        self.assertLess(
            len(ticket.description),
            len(ticket.description_full),
            "summary should be shorter than the full content",
        )

    def test_short_description_not_flagged(self):
        ticket = self._create_ticket("<p>Mensagem curta.</p>")
        self.assertFalse(ticket.has_description_full)

    def test_load_full_chunk_reconstructs_content(self):
        ticket = self._create_ticket(self._big_description())
        offset = 0
        html = ""
        while offset is not False:
            result = ticket.load_optimizer_full_chunk("description_full", offset, 25)
            html += result["html"]
            offset = result["next_offset"]
        self.assertIn("Linha 0", html)

    def test_chunk_rejects_unknown_field(self):
        ticket = self._create_ticket("<p>x</p>")
        with self.assertRaises(ValueError):
            ticket.load_optimizer_full_chunk("name", 0, 25)
