from odoo import api, fields, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    active_no_reply = fields.Boolean(string="Use no-reply email")

    @api.onchange("active_no_reply")
    def _onchange_active_no_reply(self):
        template_id = self.env.context.get("default_template_id")
        if template_id:
            mail_template = self.env["mail.template"].browse(template_id)
            if mail_template:
                mail_template.active_no_reply = self.active_no_reply
                mail_template._onchange_active_no_reply()
        else:
            if self.active_no_reply and self.env.user.company_id.email_no_reply:
                self.email_from = self.env.user.company_id.email_no_reply
                self.reply_to = self.env.user.company_id.email_no_reply
            else:
                self.email_from = False
                self.reply_to = False

    @api.model
    def create(self, vals):
        if vals.get("active_no_reply") and self.env.user.company_id.email_no_reply:
            vals["email_from"] = self.env.user.company_id.email_no_reply
            vals["reply_to"] = self.env.user.company_id.email_no_reply
        return super(MailComposer, self).create(vals)

    def send_mail_message(self, auto_commit=False):
        if self.active_no_reply and self.env.user.company_id.email_no_reply:
            self.email_from = self.env.user.company_id.email_no_reply
            self.reply_to = self.env.user.company_id.email_no_reply
        message = super(MailComposer, self).send_mail_message(auto_commit=auto_commit)
        if self.active_no_reply:
            mail_message = self.env["mail.message"].browse(message)
            mail_message.sudo().write(
                {
                    "email_from": self.env.user.company_id.email_no_reply,
                    "reply_to": self.env.user.company_id.email_no_reply,
                }
            )
        return message

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = super(MailComposer, self)._action_send_mail(
            auto_commit=auto_commit
        )
        for mail in result_mails_su:
            if mail.mail_template_id and mail.mail_template_id.active_no_reply:
                no_reply_email = self.env.user.company_id.email_no_reply
                if no_reply_email:
                    mail.write(
                        {
                            "email_from": no_reply_email,
                            "reply_to": no_reply_email,
                        }
                    )
                    if not self.env.context.get("mail_return_path"):
                        self = self.with_context(mail_return_path=no_reply_email)
        if result_messages:
            for message in result_messages:
                if message.mail_ids:
                    for mail in message.mail_ids:
                        if (
                            self.active_no_reply
                            and self.env.user.company_id.email_no_reply
                        ):
                            mail.write(
                                {
                                    "email_from": self.env.user.company_id.email_no_reply,
                                    "reply_to": self.env.user.company_id.email_no_reply,
                                }
                            )

        return result_mails_su, result_messages
