from odoo import fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    required_support_document = fields.Boolean(
        string="Required Supported Document",
    )
