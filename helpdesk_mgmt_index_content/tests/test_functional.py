# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttachmentIndexContent(TransactionCase):
    def test_ticket_search_by_attachment_content(self):
        ticket = self.env["helpdesk.ticket"].create(
            {"name": "Ticket", "description": "Ticket description"}
        )
        self.assertFalse(ticket.attachment_index_content)
        self.env["ir.attachment"].create(
            {
                "name": "note.txt",
                "mimetype": "text/plain",
                "datas": base64.b64encode(b"unique-needle-content"),
                "res_model": "helpdesk.ticket",
                "res_id": ticket.id,
            }
        )
        ticket.invalidate_recordset()
        self.assertIn("unique-needle-content", ticket.attachment_index_content)
        found = self.env["helpdesk.ticket"].search(
            [("attachment_index_content", "ilike", "unique-needle")]
        )
        self.assertIn(ticket, found)
