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

    @api.model_create_multi
    def create(self, vals_list):
        no_reply = self.env.user.company_id.email_no_reply
        if no_reply:
            for vals in vals_list:
                if vals.get("active_no_reply"):
                    vals["email_from"] = no_reply
                    vals["reply_to"] = no_reply
        return super().create(vals_list)

    def get_mail_values(self, res_ids):
        """Force the no-reply address BEFORE the mails are created and sent."""
        results = super().get_mail_values(res_ids)
        no_reply = self.env.user.company_id.email_no_reply
        if no_reply and (self.active_no_reply or self.template_id.active_no_reply):
            for values in results.values():
                values["email_from"] = no_reply
                values["reply_to"] = no_reply
        return results
