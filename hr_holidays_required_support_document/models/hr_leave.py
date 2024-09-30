from odoo import _, models
from odoo.exceptions import ValidationError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    def action_approve(self):
        for record in self:
            if (
                record.holiday_status_id.required_support_document
                and not record.supported_attachment_ids
            ):
                raise ValidationError(
                    _("Unable to approve, supporting document was not attached")
                )
        return super(HolidaysRequest, self).action_approve()
