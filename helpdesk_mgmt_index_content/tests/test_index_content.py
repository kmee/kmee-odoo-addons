# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttachmentIndexContent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Ticket = cls.env["helpdesk.ticket"]
        # a team keeps the tests valid when stage tracking modules are installed
        team = cls.env["helpdesk.ticket.team"].create({"name": "Index team"})
        vals = {"description": "d", "team_id": team.id}
        cls.ticket = cls.Ticket.create(dict(vals, name="Ticket"))
        cls.other = cls.Ticket.create(dict(vals, name="Other"))

    def _attach(self, ticket, text, name="note.txt"):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "mimetype": "text/plain",
                "datas": base64.b64encode(text.encode()),
                "res_model": "helpdesk.ticket",
                "res_id": ticket.id,
            }
        )

    def test_ticket_without_attachment_has_no_content(self):
        """Given a ticket without attachments
        When the index content is computed
        Then it is empty and a search by content does not return it."""
        self.assertFalse(self.ticket.attachment_index_content)
        found = self.Ticket.search([("attachment_index_content", "ilike", "needle")])
        self.assertNotIn(self.ticket, found)

    def test_ticket_search_by_attachment_content(self):
        """Given a ticket with a text attachment
        When searching by a word inside the attachment
        Then only that ticket is found."""
        self._attach(self.ticket, "unique-needle-content")
        self._attach(self.other, "something else entirely")
        self.assertIn("unique-needle-content", self.ticket.attachment_index_content)
        found = self.Ticket.search(
            [("attachment_index_content", "ilike", "unique-needle")]
        )
        self.assertIn(self.ticket, found)
        self.assertNotIn(self.other, found)

    def test_multiple_attachments_are_joined(self):
        """Given a ticket with two text attachments
        When the index content is computed
        Then both contents are joined by a space."""
        self._attach(self.ticket, "alpha-word", "a.txt")
        self._attach(self.ticket, "beta-word", "b.txt")
        content = self.ticket.attachment_index_content
        self.assertIn("alpha-word", content)
        self.assertIn("beta-word", content)
        self.assertEqual(len(content.split(" ")), 2)

    def test_empty_attachment_content_is_ignored(self):
        """Given a ticket with a text attachment and a link without index content
        When the index content is computed
        Then no extra separator is added for the empty one."""
        self._attach(self.ticket, "solo-word")
        self.env["ir.attachment"].create(
            {
                "name": "link",
                "type": "url",
                "url": "https://example.com",
                "res_model": "helpdesk.ticket",
                "res_id": self.ticket.id,
            }
        )
        self.assertEqual(self.ticket.attachment_index_content, "solo-word")

    def test_removing_attachment_recomputes_content(self):
        """Given a ticket whose attachment is indexed
        When the attachment is deleted
        Then the content is cleared and the search no longer finds the ticket."""
        att = self._attach(self.ticket, "vanishing-word")
        self.assertIn("vanishing-word", self.ticket.attachment_index_content)
        att.unlink()
        self.assertFalse(self.ticket.attachment_index_content)
        found = self.Ticket.search([("attachment_index_content", "ilike", "vanishing")])
        self.assertNotIn(self.ticket, found)

    def test_changing_attachment_data_recomputes_content(self):
        """Given an indexed attachment
        When its data is replaced
        Then the ticket content reflects the new text only."""
        att = self._attach(self.ticket, "old-text-here")
        att.write(
            {"datas": base64.b64encode(b"brand-new-text"), "mimetype": "text/plain"}
        )
        self.assertIn("brand-new-text", self.ticket.attachment_index_content)
        self.assertNotIn("old-text-here", self.ticket.attachment_index_content)

    def test_search_view_exposes_attachment_content(self):
        """Given the ticket search view
        When it is rendered
        Then the attachment content field is searchable there."""
        arch = etree.fromstring(self.Ticket.get_view(view_type="search")["arch"])
        self.assertTrue(arch.xpath("//field[@name='attachment_index_content']"))
