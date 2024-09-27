from odoo import models


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = "applicant.get.refuse.reason"

    def action_open_selected_mail_template(self):
        if self.send_mail and self.template_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "mail.compose.message",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_model": "hr.applicant",
                    "default_res_id": self.applicant_ids[0].id,
                    "default_template_id": self.template_id.id,
                    "force_email": True,
                    "refuse_reason_wizard_id": self.id,
                },
            }
        return
