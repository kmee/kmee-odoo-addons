from odoo import api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    active_no_reply = fields.Boolean(string="Use no-reply email")

    @api.onchange("active_no_reply")
    def _onchange_active_no_reply(self):
        if self.active_no_reply and self.env.user.company_id.email_no_reply:
            self.email_from = self.env.user.company_id.email_no_reply
            self.reply_to = self.env.user.company_id.email_no_reply
        if not self.active_no_reply:
            self.email_from = False
            self.reply_to = False
