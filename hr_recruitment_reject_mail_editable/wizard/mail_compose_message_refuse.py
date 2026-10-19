from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def action_send_mail(self):
        """
        This method calls the action_refuse_reason_apply
        method of applicant.get.refuse.reason
        if the wizard has been opened by the same
        """
        result = super(MailComposeMessage, self).action_send_mail()
        if self.env.context.get(
            "default_model"
        ) == "hr.applicant" and self.env.context.get("refuse_reason_wizard_id"):
            refuse_wizard = self.env["applicant.get.refuse.reason"].browse(
                self.env.context["refuse_reason_wizard_id"]
            )
            if refuse_wizard:
                # O e-mail (editado) ja foi enviado pelo compositor: sem isto o
                # wizard enviaria o modelo original uma segunda vez.
                refuse_wizard.send_mail = False
                refuse_wizard.action_refuse_reason_apply()

        return result
