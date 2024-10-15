from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    supported_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Supporting Documents",
        help="Attach any supporting documents here.",
    )

    @api.model
    def create(self, vals):
        # Cria o registro do leave
        leave = super(HolidaysRequest, self).create(vals)

        # Associa os anexos ao registro criado
        if vals.get("supported_attachment_ids"):
            leave.supported_attachment_ids.write(
                {
                    "res_id": leave.id,
                    "res_model": "hr.leave",
                }
            )

        return leave

    def write(self, vals):
        # Atualiza o registro do leave
        res = super(HolidaysRequest, self).write(vals)

        for record in self:
            if (
                record.holiday_status_id.required_support_document
                and not record.supported_attachment_ids
            ):
                raise ValidationError(
                    _("Unable to approve, supporting document was not attached")
                )

            # Verifica e associa os anexos ao registro se necessário
            if "supported_attachment_ids" in vals:
                record.supported_attachment_ids.write(
                    {
                        "res_id": record.id,
                        "res_model": "hr.leave",
                    }
                )

        return res
