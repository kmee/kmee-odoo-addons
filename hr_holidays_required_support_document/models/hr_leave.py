from odoo import _, api, models
from odoo.exceptions import ValidationError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    @api.model_create_multi
    def create(self, vals_list):
        holidays = super(HolidaysRequest, self).create(vals_list)
        for holiday in holidays:
            if (
                holiday.holiday_status_id.required_support_document
                and not holiday.supported_attachment_ids
            ):
                raise ValidationError(
                    _(
                        "É necessário anexar um documento de suporte para este tipo de folga."
                    )
                )
        return holidays
