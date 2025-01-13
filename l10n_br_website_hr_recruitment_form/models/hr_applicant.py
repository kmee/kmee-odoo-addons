# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import uuid

from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    access_token = fields.Char(
        "Security Token",
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )

    form_url = fields.Char(compute="_compute_form_url")

    @api.depends("access_token")
    def _compute_form_url(self):
        for applicant in self:
            applicant.form_url = (
                applicant.get_share_url() if applicant.access_token else ""
            )

    def get_share_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return f"{base_url}/application/{self.id}/form?access_token={self.access_token}"

    def action_share_applicant_form(self):
        self.ensure_one()
        template_id = self.env.ref(
            "l10n_br_website_hr_recruitment_form.send_applicant_form"
        )
        return self.with_context(force_send=True).message_post_with_template(
            template_id.id,
            composition_mode="comment",
        )
