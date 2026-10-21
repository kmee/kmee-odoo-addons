# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import is_html_empty

BUTTON_STYLE = "border-radius: 3px"


@tagged("post_install", "-at_install")
class TestNotificationButton(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Record"})
        cls.message = cls.partner.message_post(body="Hello world")

    def _render(self, title, has_button_access=True):
        values = {
            "lang": "en_US",
            "subtype": self.env["mail.message.subtype"],
            "message": self.message,
            "has_button_access": has_button_access,
            "button_access": {"url": "http://localhost/x", "title": title},
            "subtitles": ["Subtitle"],
            "actions": [],
            "is_discussion": True,
            "company": self.env.company,
            "record_name": "Record",
            "tracking_values": [],
            "email_add_signature": False,
            "signature": "",
            "is_html_empty": is_html_empty,
            "preview": "",
        }
        return str(
            self.env["ir.qweb"]._render(
                "mail.mail_notification_layout", values, minimal_qcontext=True
            )
        )

    def test_regular_document_keeps_access_button(self):
        """Given a notification for a non invoice document
        When the layout is rendered
        Then the access button is present."""
        html = self._render("View Task")
        self.assertIn(BUTTON_STYLE, html)
        self.assertIn("View Task", html)

    def test_invoice_title_removes_button(self):
        """Given a notification whose access button is "View Invoice"
        When the layout is rendered
        Then the button cell is removed but the message body stays."""
        html = self._render("View Invoice")
        self.assertNotIn(BUTTON_STYLE, html)
        self.assertIn("Hello world", html)

    def test_journal_entry_title_removes_button(self):
        """Given a notification whose access button is "View Journal Entry"
        When rendered
        Then the button is removed."""
        self.assertNotIn(BUTTON_STYLE, self._render("View Journal Entry"))

    def test_portuguese_titles_remove_button(self):
        """Given the Portuguese titles "Ver Fatura" and "Ver Lançamento"
        When rendered
        Then the button is removed in both cases."""
        self.assertNotIn(BUTTON_STYLE, self._render("Ver Fatura"))
        self.assertNotIn(BUTTON_STYLE, self._render("Ver Lançamento"))

    def test_no_button_access_renders_no_button(self):
        """Given a notification without button access
        When rendered
        Then there is no button, regardless of the title (control for the xpath)."""
        self.assertNotIn(
            BUTTON_STYLE, self._render("View Task", has_button_access=False)
        )
