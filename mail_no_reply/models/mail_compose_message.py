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
