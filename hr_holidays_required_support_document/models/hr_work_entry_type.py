from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    required_support_document = fields.Boolean(
        string="Required Supported Document",
    )
