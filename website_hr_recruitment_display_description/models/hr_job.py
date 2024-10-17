from odoo import fields, models


class Job(models.Model):
    _inherit = "hr.job"

    website_display_description = fields.Boolean()
