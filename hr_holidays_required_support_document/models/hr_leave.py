from odoo import _, models
from odoo.exceptions import ValidationError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    def action_approve(self):
        for record in self:
            if (
                record.holiday_status_id.force_support_document
                and not record.supported_attachment_ids
            ):
                raise ValidationError(
                    _("Request supported document of this employee's case")
                )
        return super(HolidaysRequest, self).action_approve()
