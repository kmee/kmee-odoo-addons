from odoo import fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    force_support_document = fields.Boolean(
        string="Force Supported Document",
    )
