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

    def _big_description(self, lines=120):
        return (
            "<div>"
            + "".join(
                "<p>Linha %d de conteudo sem dados pessoais.</p>" % i
                for i in range(lines)
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

    def _text_len(self, html):
        return self.env["helpdesk.ticket"]._optimizer_sanitizer().text_content_length(
            html
        )

    def test_source_kept_intact_and_summary_shorter(self):
        big = self._big_description()
        ticket = self._create_ticket(big)
        self.assertIn("Linha 0", ticket.description)
        self.assertIn("Linha 119", ticket.description)
        self.assertEqual(self._text_len(ticket.description), self._text_len(big))
        self.assertTrue(ticket.has_description_full)
        self.assertLess(
            self._text_len(ticket.description_summary),
            self._text_len(ticket.description),
        )

    def test_short_description_not_flagged(self):
        ticket = self._create_ticket("<p>Mensagem curta.</p>")
        self.assertFalse(ticket.has_description_full)
        self.assertEqual(ticket.description, "<p>Mensagem curta.</p>")

    def test_edit_preserves_full_content(self):
        ticket = self._create_ticket(self._big_description())
        original_text_len = self._text_len(ticket.description)
        ticket.write({"description": ticket.description + "<p>EDICAO TESTE B4</p>"})
        self.assertIn("Linha 0", ticket.description)
        self.assertIn("EDICAO TESTE B4", ticket.description)
        self.assertGreater(self._text_len(ticket.description), original_text_len)
        self.assertTrue(ticket.has_description_full)

    def test_duplicate_preserves_full_content(self):
        ticket = self._create_ticket(self._big_description())
        copy = ticket.copy()
        self.assertEqual(copy.description, ticket.description)
        self.assertTrue(copy.has_description_full)
        self.assertLess(
            self._text_len(copy.description_summary),
            self._text_len(copy.description),
        )

    def test_summary_recomputed_on_description_change(self):
        ticket = self._create_ticket("<p>curta</p>")
        self.assertFalse(ticket.has_description_full)
        ticket.write({"description": self._big_description()})
        self.assertTrue(ticket.has_description_full)
        self.assertIn("Linha 0", ticket.description)
