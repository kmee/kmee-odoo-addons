# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo.tests.common import TransactionCase, tagged

NO_REPLY = "no-reply@example.com"
SALES = "sales@example.com"


@tagged("post_install", "-at_install")
class TestMailNoReply(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.user.company_id
        cls.company.email_no_reply = NO_REPLY
        cls.partner = cls.env["res.partner"].create(
            {"name": "Dest", "email": "dest@example.com"}
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "No reply template",
                "model_id": cls.env["ir.model"]._get_id("res.partner"),
                "subject": "Hello",
                "body_html": "<p>Hello</p>",
                "email_from": SALES,
                "reply_to": SALES,
                "email_to": "dest@example.com",
                "auto_delete": False,
            }
        )
        cls.Composer = cls.env["mail.compose.message"]

    def _composer(self, **kw):
        vals = {
            "composition_mode": "comment",
            "model": "res.partner",
            "res_ids": self.partner.ids,
            "subject": "Test",
            "body": "<p>Test</p>",
        }
        vals.update(kw)
        return self.Composer.create(vals)

    def _mass_composer(self, **kw):
        vals = {
            "composition_mode": "mass_mail",
            "model": "res.partner",
            "res_ids": self.partner.ids,
            "template_id": self.template.id,
            "auto_delete": False,
        }
        vals.update(kw)
        return self.Composer.with_context(active_ids=self.partner.ids).create(vals)

    def test_company_setting_is_written_through_config_settings(self):
        """Given the settings wizard
        When the no-reply email is filled
        Then it is stored in the company."""
        self.env["res.config.settings"].create({"email_no_reply": "other@example.com"})
        self.assertEqual(self.company.email_no_reply, "other@example.com")

    def test_composer_create_uses_no_reply_address(self):
        """Given a company no-reply address
        When a composer is created with the toggle on
        Then From and Reply-To are the no-reply address."""
        composer = self._composer(active_no_reply=True)
        self.assertEqual(composer.email_from, NO_REPLY)
        self.assertEqual(composer.reply_to, NO_REPLY)

    def test_composer_create_without_toggle_keeps_sender(self):
        """Given a company no-reply address
        When the composer toggle is off
        Then the no-reply address is not applied."""
        composer = self._composer(email_from=SALES, reply_to=SALES)
        self.assertEqual(composer.email_from, SALES)
        self.assertEqual(composer.reply_to, SALES)

    def test_composer_create_without_company_address_keeps_sender(self):
        """Given a company without no-reply address
        When the composer toggle is on
        Then the sender given by the user is kept."""
        self.company.email_no_reply = False
        composer = self._composer(
            active_no_reply=True, email_from=SALES, reply_to=SALES
        )
        self.assertEqual(composer.email_from, SALES)

    def test_composer_onchange_toggles_addresses(self):
        """Given a composer without template
        When the toggle goes on and then off
        Then the addresses are set and then cleared."""
        composer = self.Composer.new({"active_no_reply": True})
        composer._onchange_active_no_reply()
        self.assertEqual(composer.email_from, NO_REPLY)
        self.assertEqual(composer.reply_to, NO_REPLY)
        composer.active_no_reply = False
        composer._onchange_active_no_reply()
        self.assertFalse(composer.email_from)
        self.assertFalse(composer.reply_to)

    def test_composer_onchange_propagates_to_template(self):
        """Given a composer opened from a template
        When the toggle is switched on
        Then the template gets the flag and the no-reply addresses."""
        composer = self.Composer.with_context(default_template_id=self.template.id).new(
            {"active_no_reply": True}
        )
        composer._onchange_active_no_reply()
        self.assertTrue(self.template.active_no_reply)
        self.assertEqual(self.template.email_from, NO_REPLY)

    def test_template_onchange_toggles_addresses(self):
        """Given a mail template
        When the toggle goes on and off
        Then From/Reply-To are set and cleared; without company address they stay empty."""
        template = self.env["mail.template"].new({"active_no_reply": True})
        template._onchange_active_no_reply()
        self.assertEqual(template.email_from, NO_REPLY)
        self.assertEqual(template.reply_to, NO_REPLY)
        template.active_no_reply = False
        template._onchange_active_no_reply()
        self.assertFalse(template.email_from)
        self.company.email_no_reply = False
        template.active_no_reply = True
        template._onchange_active_no_reply()
        self.assertFalse(template.email_from)

    def test_comment_mode_message_uses_no_reply_sender(self):
        """Given a composer in comment mode with the toggle on
        When the message is sent
        Then the posted message is authored from the no-reply address."""
        composer = self._composer(active_no_reply=True, partner_ids=self.partner.ids)
        _mails, messages = composer._action_send_mail()
        self.assertEqual(messages.email_from, NO_REPLY)

    def test_comment_mode_without_toggle_keeps_default_sender(self):
        """Given a composer in comment mode with the toggle off
        When the message is sent
        Then the message is not from the no-reply address."""
        composer = self._composer(partner_ids=self.partner.ids)
        _mails, messages = composer._action_send_mail()
        self.assertNotEqual(messages.email_from, NO_REPLY)

    def test_mass_mail_template_flag_sets_mail_sender(self):
        """Given a template flagged as no-reply
        When a mass mail is sent
        Then the mail record has the no-reply From/Reply-To."""
        self.template.active_no_reply = True
        mails, _messages = self._mass_composer()._action_send_mail()
        self.assertEqual(mails.mapped("email_from"), [NO_REPLY])
        self.assertEqual(mails.mapped("reply_to"), [NO_REPLY])

    def test_mass_mail_outgoing_message_header_is_no_reply(self):
        """Given a template flagged as no-reply
        When a mass mail is sent
        Then the RFC822 message handed to the SMTP layer is From the no-reply address."""
        self.template.active_no_reply = True
        # 19.0: mail.mail skips sending during tests unless _disable_send is
        # patched on the registry class (no SMTP connection either), as the
        # core mail tests do
        mail_server_cls = type(self.env["ir.mail_server"])
        with (
            mock.patch.object(mail_server_cls, "_disable_send", lambda _: False),
            mock.patch.object(mail_server_cls, "_connect__", return_value=None),
            mock.patch.object(
                mail_server_cls, "send_email", return_value="<id@x>"
            ) as send,
        ):
            self._mass_composer()._action_send_mail()
        self.assertTrue(send.called)
        sent_from = [call.args[0]["From"] for call in send.call_args_list]
        self.assertTrue(all(NO_REPLY in value for value in sent_from), sent_from)

    def test_mass_mail_without_flag_keeps_template_sender(self):
        """Given a template that is not flagged
        When a mass mail is sent
        Then the no-reply address is not forced (control)."""
        mails, _messages = self._mass_composer()._action_send_mail()
        self.assertTrue(mails)
        self.assertNotIn(NO_REPLY, mails.mapped("email_from"))
        self.assertNotIn(NO_REPLY, mails.mapped("reply_to"))
