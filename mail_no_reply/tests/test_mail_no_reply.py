from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailNoReply(TransactionCase):
    def test_composer_uses_no_reply_address(self):
        self.env.user.company_id.email_no_reply = "no-reply@example.com"
        composer = self.env["mail.compose.message"].create(
            {
                "subject": "Test",
                "body": "<p>Test</p>",
                "active_no_reply": True,
            }
        )
        self.assertEqual(composer.email_from, "no-reply@example.com")
        self.assertEqual(composer.reply_to, "no-reply@example.com")

    def test_template_onchange(self):
        self.env.user.company_id.email_no_reply = "no-reply@example.com"
        template = self.env["mail.template"].new({"active_no_reply": True})
        template._onchange_active_no_reply()
        self.assertEqual(template.email_from, "no-reply@example.com")
