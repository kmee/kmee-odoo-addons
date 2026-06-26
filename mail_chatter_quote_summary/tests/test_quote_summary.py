# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase

from ..models.mail_message import ENABLED_PARAM

GMAIL_BODY = """
<div dir="auto">Reply 2, sending to support</div>
<br/>
<div class="gmail_quote gmail_quote_container">
  <div dir="ltr" class="gmail_attr">
    On Tue, Jan 6, 2026 at 2:06 PM Maria Exemplo wrote:<br/>
  </div>
  <blockquote class="gmail_quote" style="border-left:1px #ccc solid;padding-left:1ex">
    <div>Conteudo citado anterior, ficticio, com bastante texto.</div>
  </blockquote>
</div>
"""


class TestQuoteSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.partner = cls.env["res.partner"].create({"name": "Quote Test Partner"})
        cls.message = cls.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": cls.partner.id,
                "message_type": "comment",
                "body": GMAIL_BODY,
            }
        )

    def _set_enabled(self, value):
        settings = self.env["res.config.settings"].create(
            {"quote_summary_enabled": value}
        )
        settings.execute()

    def test_disable_persists(self):
        self._set_enabled(False)
        self.assertFalse(self.env["mail.message"]._quote_summary_enabled())
        self.assertIs(self.params.get_param(ENABLED_PARAM), False)
        reopened = self.env["res.config.settings"].default_get(
            ["quote_summary_enabled"]
        )
        self.assertFalse(reopened.get("quote_summary_enabled"))

    def test_reenable_after_disable(self):
        self._set_enabled(False)
        self._set_enabled(True)
        self.assertTrue(self.env["mail.message"]._quote_summary_enabled())

    def test_message_format_summarizes_and_keeps_body(self):
        self._set_enabled(True)
        formatted = self.message.message_format()[0]
        self.assertIn("o_quote_history_btn", formatted["body"])
        self.assertNotIn("Conteudo citado anterior", formatted["body"])
        self.assertIn("Conteudo citado anterior", self.message.body)

    def test_message_format_untouched_when_disabled(self):
        self._set_enabled(False)
        formatted = self.message.message_format()[0]
        self.assertNotIn("o_quote_history_btn", formatted["body"])

    def test_load_history_chunk_reconstructs(self):
        chunk = self.message.load_quote_history_chunk(0, 25)
        self.assertIn("Conteudo citado anterior", chunk["html"])
