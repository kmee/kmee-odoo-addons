from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
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
        return super(MailComposeMessage, self).create(vals)
